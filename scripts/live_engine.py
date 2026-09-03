"""
SIH26052 - Live audio engine (internal round, pretrained model only).

    mic  ->  DeepFilterNet3 (100 ms blocks)  ->  headphones

While running it also serves the WebSocket contract in ui_contract/WEBSOCKET_CONTRACT.md:
it PUSHES `status` / `waveform` / `metrics` / `error` and ACCEPTS `start` / `stop`
/ `set_model` commands. Audio never leaves Python; the UI only draws data and
sends button presses.

Design notes (agreed with the team):
  * Output MUST be headphones, never a speaker, to avoid mic->speaker feedback.
  * Single mic, mono (DeepFilterNet3 is mono).
  * 100 ms processing blocks: ~4.6x real-time headroom, ~80-140 ms latency.
    (The "10-40 ms" doc claim is not reachable on the enhance() path.)
  * Three audible states:
        Stopped              -> SILENCE (headphones idle, comfortable to wear)
        Running + model OFF  -> raw noisy audio  (the "before")
        Running + model ON   -> cleaned speech   (the "after")
    Stop truly silences the output. The model toggle only matters while running,
    and the pipeline defaults to model ON so nobody gets an unexpected earful.

Run:
    .\.venv\Scripts\python.exe scripts\live_engine.py            # engine + WebSocket
    .\.venv\Scripts\python.exe scripts\live_engine.py --list     # list audio devices
    .\.venv\Scripts\python.exe scripts\live_engine.py --input 1 --output 14
    .\.venv\Scripts\python.exe scripts\live_engine.py --self-test # 3 s mic->headphones, no UI

The UI (mock or real) connects to  ws://127.0.0.1:8000/ws  - identical either way.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import queue
import sys
import threading
import time
from dataclasses import dataclass, field

import numpy as np

# ------------------------------------------------------------------ constants

SAMPLE_RATE = 48_000          # DeepFilterNet3 operates at 48 kHz
BLOCK_MS = 100                # processing block size (settled by block_size_sweep)
BLOCK_SAMPLES = SAMPLE_RATE * BLOCK_MS // 1000     # 4800
WAVEFORM_POINTS = 200         # downsampled points per waveform message
WAVEFORM_HZ = 15              # waveform messages per second
METRICS_HZ = 4                # metrics messages per second

WS_HOST = "127.0.0.1"
WS_PORT = 8000


# ------------------------------------------------------------------ metrics

def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x.astype(np.float64) ** 2) + 1e-12))


def estimate_snr_db(signal: np.ndarray) -> float:
    """
    Rough single-channel SNR estimate for display only (NOT a scientific metric).

    We don't have a clean reference in a live mic stream, so we approximate:
    treat the loudest energy as "speech+noise" and the quietest 20% of short
    frames as the "noise floor". SNR ~= 10*log10(peak_energy / floor_energy).
    Good enough to show the bar move; the headline improvement number comes
    from comparing the input estimate to the output estimate.
    """
    if signal.size == 0:
        return 0.0
    frame = max(1, len(signal) // 20)
    energies = []
    for i in range(0, len(signal) - frame + 1, frame):
        seg = signal[i:i + frame]
        energies.append(float(np.mean(seg.astype(np.float64) ** 2) + 1e-12))
    if not energies:
        return 0.0
    energies = np.array(energies)
    floor = float(np.percentile(energies, 20))
    peak = float(np.percentile(energies, 95))
    return float(10.0 * np.log10((peak + 1e-12) / (floor + 1e-12)))


def downsample_for_display(block: np.ndarray, points: int = WAVEFORM_POINTS) -> list[float]:
    """Reduce a raw audio block to `points` values for plotting (peak-preserving)."""
    if block.size == 0:
        return [0.0] * points
    if len(block) <= points:
        return [round(float(v), 4) for v in block]
    # peak-preserving downsample: max-abs within each bucket, keep the sign
    idx = np.linspace(0, len(block), points + 1).astype(int)
    out = []
    for a, b in zip(idx[:-1], idx[1:]):
        seg = block[a:b] if b > a else block[a:a + 1]
        j = int(np.argmax(np.abs(seg)))
        out.append(round(float(seg[j]), 4))
    return out


# ------------------------------------------------------------- shared state

@dataclass
class EngineState:
    """Thread-safe-ish shared state between the audio thread and the WS server."""
    running: bool = False
    model_on: bool = True          # default ON so nobody gets an earful of raw noise
    started_at: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)

    # latest data for the WS server to publish (written by audio thread)
    last_noisy_disp: list[float] = field(default_factory=lambda: [0.0] * WAVEFORM_POINTS)
    last_clean_disp: list[float] = field(default_factory=lambda: [0.0] * WAVEFORM_POINTS)
    snr_in_db: float = 0.0
    snr_out_db: float = 0.0
    dnsmos: float | None = None
    latency_ms: float = 0.0
    rtf: float = 0.0

    def status_dict(self, message: str = "ok") -> dict:
        return {
            "type": "status",
            "running": self.running,
            "model_on": self.model_on,
            "sample_rate": SAMPLE_RATE,
            "block_ms": BLOCK_MS,
            "message": message,
        }


# ------------------------------------------------------------- audio engine

class AudioEngine:
    """
    Owns the DeepFilterNet3 model and the sounddevice streams.

    Runs its own worker thread that pulls mic blocks off a queue, enhances them,
    and pushes results to the headphones. The WebSocket server reads the latest
    display data straight off EngineState.
    """

    def __init__(self, state: EngineState, input_device=None, output_device=None):
        self.state = state
        self.input_device = input_device
        self.output_device = output_device

        self._in_q: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=32)
        self._worker: threading.Thread | None = None
        self._stop_worker = threading.Event()

        self._in_stream = None
        self._out_stream = None

        # loaded lazily so --list is instant and import errors surface clearly
        self.model = None
        self.df_state = None
        self.enhance = None

    # -- model ------------------------------------------------------------
    def load_model(self) -> None:
        if self.model is not None:
            return
        print("Loading pretrained DeepFilterNet3 ...", flush=True)
        from df.enhance import enhance, init_df
        model, df_state, _ = init_df(config_allow_defaults=True)
        self.model, self.df_state, self.enhance = model, df_state, enhance
        sr = df_state.sr()
        if sr != SAMPLE_RATE:
            print(f"  WARNING: model sr {sr} != engine sr {SAMPLE_RATE}", flush=True)
        print(f"  model ready (sr={sr} Hz)", flush=True)

    def _enhance_block(self, block: np.ndarray) -> np.ndarray:
        import torch
        t = torch.from_numpy(block).unsqueeze(0)
        out = self.enhance(self.model, self.df_state, t).squeeze(0).numpy()
        # enhance() can return a slightly different length; pad/crop to block size
        if len(out) < len(block):
            out = np.pad(out, (0, len(block) - len(out)))
        elif len(out) > len(block):
            out = out[:len(block)]
        return out.astype(np.float32)

    # -- sounddevice callbacks -------------------------------------------
    def _input_callback(self, indata, frames, time_info, status):
        if status:
            # overflow etc. - non-fatal, just note it
            pass
        # indata: (frames, channels) float32; take channel 0 (mono)
        mono = indata[:, 0].copy()
        try:
            self._in_q.put_nowait(mono)
        except queue.Full:
            # drop the oldest to stay real-time
            try:
                self._in_q.get_nowait()
                self._in_q.put_nowait(mono)
            except queue.Empty:
                pass

    # -- worker thread ----------------------------------------------------
    def _run_worker(self) -> None:
        import sounddevice as sd

        self.load_model()

        # warm up the model so the first real block isn't slow
        warm = np.zeros(BLOCK_SAMPLES, dtype=np.float32)
        for _ in range(2):
            self._enhance_block(warm)

        # open output stream (headphones) and input stream (mic), mono.
        try:
            self._out_stream = sd.OutputStream(
                samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                device=self.output_device, blocksize=BLOCK_SAMPLES,
            )
            self._out_stream.start()

            self._in_stream = sd.InputStream(
                samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                device=self.input_device, blocksize=BLOCK_SAMPLES,
                callback=self._input_callback,
            )
            self._in_stream.start()
        except Exception as exc:  # bad device, unsupported format, etc.
            print(f"\n!! AUDIO STREAM ERROR: {exc}", flush=True)
            print("   The mic or headphone device could not be opened at "
                  f"{SAMPLE_RATE} Hz mono.", flush=True)
            print("   Run  --list  and pass --input / --output explicitly.", flush=True)
            return

        # report what actually got opened so device problems are obvious
        try:
            in_name = sd.query_devices(self._in_stream.device, "input")["name"]
            out_name = sd.query_devices(self._out_stream.device, "output")["name"]
            print(f"  mic  IN  -> {in_name}", flush=True)
            print(f"  head OUT -> {out_name}", flush=True)
        except Exception:
            pass

        silence = np.zeros(BLOCK_SAMPLES, dtype=np.float32)

        try:
            while not self._stop_worker.is_set():
                try:
                    block = self._in_q.get(timeout=0.2)
                except queue.Empty:
                    continue

                with self.state.lock:
                    running = self.state.running
                    model_on = self.state.model_on

                if not running:
                    # Stopped -> feed silence to headphones (comfortable to wear)
                    self._out_stream.write(silence)
                    continue

                t0 = time.perf_counter()
                if model_on:
                    clean = self._enhance_block(block)
                else:
                    clean = block  # bypass: judges hear the raw "before"
                compute_ms = (time.perf_counter() - t0) * 1000.0

                # play it
                self._out_stream.write(np.clip(clean, -1.0, 1.0))

                # update display + metrics for the WS server
                self._publish(block, clean, compute_ms, model_on)
        finally:
            for s in (self._in_stream, self._out_stream):
                try:
                    if s is not None:
                        s.stop(); s.close()
                except Exception:
                    pass

    def _publish(self, noisy: np.ndarray, clean: np.ndarray,
                 compute_ms: float, model_on: bool) -> None:
        snr_in = estimate_snr_db(noisy)
        snr_out = estimate_snr_db(clean) if model_on else snr_in
        with self.state.lock:
            self.state.last_noisy_disp = downsample_for_display(noisy)
            self.state.last_clean_disp = downsample_for_display(clean)
            self.state.snr_in_db = snr_in
            self.state.snr_out_db = snr_out
            self.state.latency_ms = round(BLOCK_MS + compute_ms, 1)  # block + compute
            self.state.rtf = round(compute_ms / BLOCK_MS, 3)
            # dnsmos left as None live (no reference); UI shows "-"

    # -- lifecycle --------------------------------------------------------
    def start_worker(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._stop_worker.clear()
        self._worker = threading.Thread(target=self._run_worker, daemon=True)
        self._worker.start()

    def stop_worker(self) -> None:
        self._stop_worker.set()
        if self._worker:
            self._worker.join(timeout=3.0)


# --------------------------------------------------------------- WS server

async def ws_handler(websocket, state: EngineState, engine: AudioEngine):
    import websockets

    async def send(obj: dict):
        await websocket.send(json.dumps(obj))

    await send(state.status_dict("connected"))

    async def push_loop():
        wave_interval = 1.0 / WAVEFORM_HZ
        metrics_interval = 1.0 / METRICS_HZ
        last_metrics = 0.0
        try:
            while True:
                with state.lock:
                    running = state.running
                    t = (time.time() - state.started_at) if running else 0.0
                    noisy = list(state.last_noisy_disp)
                    clean = list(state.last_clean_disp)
                    snr_in = state.snr_in_db
                    snr_out = state.snr_out_db
                    dnsmos = state.dnsmos
                    latency = state.latency_ms
                    rtf = state.rtf
                if running:
                    await send({
                        "type": "waveform",
                        "t": round(t, 2),
                        "noisy": noisy,
                        "clean": clean,
                    })
                    now = time.time()
                    if now - last_metrics >= metrics_interval:
                        improvement = round(snr_out - snr_in, 2)
                        await send({
                            "type": "metrics",
                            "t": round(t, 2),
                            "snr_in_db": round(snr_in, 2),
                            "snr_out_db": round(snr_out, 2),
                            "snr_improvement_db": improvement,
                            "dnsmos": dnsmos,
                            "latency_ms": latency,
                            "rtf": rtf,
                        })
                        last_metrics = now
                await asyncio.sleep(wave_interval)
        except websockets.ConnectionClosed:
            return

    pusher = asyncio.create_task(push_loop())
    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await send({"type": "error", "message": "invalid JSON"})
                continue
            if msg.get("type") != "command":
                continue
            action = msg.get("action")
            if action == "start":
                with state.lock:
                    state.running = True
                    state.started_at = time.time()
                await send(state.status_dict("started"))
            elif action == "stop":
                with state.lock:
                    state.running = False
                await send(state.status_dict("stopped"))
            elif action == "set_model":
                with state.lock:
                    state.model_on = bool(msg.get("on", True))
                    onoff = "on" if state.model_on else "off"
                await send(state.status_dict(f"model {onoff}"))
            else:
                await send({"type": "error", "message": f"unknown action: {action!r}"})
    except websockets.ConnectionClosed:
        pass
    finally:
        pusher.cancel()


async def serve(state: EngineState, engine: AudioEngine) -> None:
    import websockets
    engine.start_worker()  # audio thread runs continuously; Stop just feeds silence
    print(f"Live engine WebSocket : ws://{WS_HOST}:{WS_PORT}/ws")
    print("  (same contract as the mock server; connect the UI here)")
    print("  starts STOPPED + model ON. Send a start command to go live.")
    async with websockets.serve(
        lambda ws: ws_handler(ws, state, engine),
        WS_HOST, WS_PORT,
    ):
        await asyncio.Future()  # run forever


# ----------------------------------------------------------------- helpers

def list_devices() -> None:
    import sounddevice as sd
    print(sd.query_devices())
    print("\nDefault [input, output]:", sd.default.device)
    print("\nTip: pick your headphones as --output and your mic as --input.")


def self_test(engine: AudioEngine, seconds: float = 10.0) -> None:
    """Run mic->model->headphones with NO WebSocket, model ON.

    Loads the model and opens the audio streams FIRST, then opens a clearly
    marked listening window so the whole window is real audio time (not model
    load time). Talk during the window; you should hear cleaned audio.
    """
    # 1) load the model up front (this is the slow part - keep it out of the window)
    engine.load_model()

    # 2) start the audio worker and give the streams a moment to open
    engine.start_worker()
    engine.state.model_on = True
    print("\nOpening mic and headphone streams ...", flush=True)
    time.sleep(1.5)  # let InputStream/OutputStream actually start

    # 3) now the real listening window
    engine.state.started_at = time.time()
    engine.state.running = True
    print("\n" + "=" * 60)
    print(f"  LISTENING NOW - TALK INTO THE MIC for {seconds:.0f} seconds.")
    print("  Play your gunfire/helicopter noise near the mic.")
    print("  You should hear your voice with the noise reduced.")
    print("=" * 60, flush=True)
    try:
        for remaining in range(int(seconds), 0, -1):
            print(f"  ... {remaining:2d}s left", flush=True)
            time.sleep(1.0)
    finally:
        engine.state.running = False
        time.sleep(0.3)
        engine.stop_worker()
    print("\nSelf-test done. Did you hear your voice cleaned?")


def main() -> None:
    ap = argparse.ArgumentParser(description="SIH26052 live audio engine")
    ap.add_argument("--list", action="store_true", help="list audio devices and exit")
    ap.add_argument("--input", default=None, help="input device index or name (mic)")
    ap.add_argument("--output", default=None, help="output device index or name (headphones)")
    ap.add_argument("--self-test", action="store_true",
                    help="3 s mic->headphones test, no WebSocket")
    args = ap.parse_args()

    if args.list:
        list_devices()
        return

    def parse_dev(v):
        if v is None:
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return v  # name substring; sounddevice resolves it

    state = EngineState()
    engine = AudioEngine(state, parse_dev(args.input), parse_dev(args.output))

    if args.self_test:
        self_test(engine)
        return

    try:
        asyncio.run(serve(state, engine))
    except KeyboardInterrupt:
        print("\nShutting down ...")
        engine.stop_worker()


if __name__ == "__main__":
    main()
