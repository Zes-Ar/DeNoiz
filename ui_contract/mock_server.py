"""
Mock backend for the SIH26052 UI — for the FRONTEND developer.

It speaks the EXACT same WebSocket contract as the real audio engine
(see WEBSOCKET_CONTRACT.md), but there is NO model and NO microphone.
It streams believable fake waveforms and metrics so the React UI can be
built and tested with zero dependency on the ML model or Python audio setup.

When the real engine is ready, it will speak the same contract, and the UI
will connect to it unchanged.

------------------------------------------------------------------------
HOW TO RUN (frontend dev only needs this):
    pip install "fastapi>=0.110" "uvicorn>=0.27"
    python mock_server.py

Then the server is at:
    ws://127.0.0.1:8000/ws        <- the UI connects here
    http://127.0.0.1:8000/        <- health check in a browser

The mock starts "stopped". Send a start command from the UI (or use the
built-in test page at http://127.0.0.1:8000/ ) to begin the fake stream.
------------------------------------------------------------------------
"""

from __future__ import annotations

import asyncio
import json
import math
import random
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="SIH26052 Mock Backend")

SAMPLE_RATE = 48_000
BLOCK_MS = 100
WAVEFORM_POINTS = 200          # points sent per waveform message
WAVEFORM_HZ = 15               # waveform messages per second
METRICS_HZ = 4                 # metrics messages per second


class SessionState:
    """Per-connection state: is it running, is the model on."""

    def __init__(self) -> None:
        self.running = False
        self.model_on = True
        self.started_at = 0.0

    def status_msg(self, message: str = "ok") -> dict:
        return {
            "type": "status",
            "running": self.running,
            "model_on": self.model_on,
            "sample_rate": SAMPLE_RATE,
            "block_ms": BLOCK_MS,
            "message": message,
        }


def fake_waveforms(t: float, model_on: bool):
    """
    Build a noisy waveform and its 'cleaned' counterpart.

    noisy = a speech-like tone + lots of noise (+ occasional 'gunshot' spikes).
    clean = the same tone with the noise mostly removed IF the model is on;
            if the model is off, clean == noisy (the demo 'before' state).
    """
    noisy = []
    clean = []
    base_freq = 180.0  # pretend fundamental of a voice
    for i in range(WAVEFORM_POINTS):
        phase = (i / WAVEFORM_POINTS) * 2 * math.pi * 6
        speech = 0.35 * math.sin(phase + t) * math.sin(0.5 * phase)
        noise = random.uniform(-0.45, 0.45)

        # occasional impulsive 'gunshot' spike
        if random.random() < 0.02:
            noise += random.choice([-1.0, 1.0]) * random.uniform(0.6, 0.95)

        n = max(-1.0, min(1.0, speech + noise))
        if model_on:
            c = max(-1.0, min(1.0, speech + noise * 0.12))  # noise strongly reduced
        else:
            c = n                                           # bypass: same as noisy
        noisy.append(round(n, 4))
        clean.append(round(c, 4))
    return noisy, clean


def fake_metrics(t: float, model_on: bool) -> dict:
    """Plausible metric numbers that wobble a little over time."""
    if model_on:
        snr_in = -3.0 + 1.5 * math.sin(t * 0.7) + random.uniform(-0.4, 0.4)
        improvement = 11.0 + 2.0 * math.sin(t * 0.3) + random.uniform(-0.6, 0.6)
        snr_out = snr_in + improvement
        dnsmos = 3.4 + 0.3 * math.sin(t * 0.4) + random.uniform(-0.1, 0.1)
    else:
        snr_in = -3.0 + 1.5 * math.sin(t * 0.7) + random.uniform(-0.4, 0.4)
        snr_out = snr_in                       # model off: no improvement
        improvement = 0.0
        dnsmos = 2.1 + 0.2 * math.sin(t * 0.4) + random.uniform(-0.1, 0.1)

    return {
        "type": "metrics",
        "t": round(t, 2),
        "snr_in_db": round(snr_in, 2),
        "snr_out_db": round(snr_out, 2),
        "snr_improvement_db": round(improvement, 2),
        "dnsmos": round(dnsmos, 2),
        "latency_ms": round(120.0 + random.uniform(-8, 8), 1),
        "rtf": round(0.22 + random.uniform(-0.03, 0.03), 3),
    }


async def stream_loop(ws: WebSocket, state: SessionState) -> None:
    """Continuously push waveform + metrics while running."""
    last_metrics = 0.0
    wave_interval = 1.0 / WAVEFORM_HZ
    metrics_interval = 1.0 / METRICS_HZ
    try:
        while True:
            if state.running:
                now = time.time()
                t = now - state.started_at

                noisy, clean = fake_waveforms(t, state.model_on)
                await ws.send_text(json.dumps({
                    "type": "waveform",
                    "t": round(t, 2),
                    "noisy": noisy,
                    "clean": clean,
                }))

                if now - last_metrics >= metrics_interval:
                    await ws.send_text(json.dumps(fake_metrics(t, state.model_on)))
                    last_metrics = now

            await asyncio.sleep(wave_interval)
    except (WebSocketDisconnect, RuntimeError):
        return


async def handle_command(ws: WebSocket, state: SessionState, msg: dict) -> None:
    action = msg.get("action")
    if action == "start":
        state.running = True
        state.started_at = time.time()
        await ws.send_text(json.dumps(state.status_msg("started")))
    elif action == "stop":
        state.running = False
        await ws.send_text(json.dumps(state.status_msg("stopped")))
    elif action == "set_model":
        state.model_on = bool(msg.get("on", True))
        await ws.send_text(json.dumps(
            state.status_msg(f"model {'on' if state.model_on else 'off'}")))
    else:
        await ws.send_text(json.dumps({
            "type": "error",
            "message": f"unknown action: {action!r}",
        }))


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    state = SessionState()
    await ws.send_text(json.dumps(state.status_msg("connected")))

    streamer = asyncio.create_task(stream_loop(ws, state))
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(json.dumps({
                    "type": "error", "message": "invalid JSON"}))
                continue
            if msg.get("type") == "command":
                await handle_command(ws, state, msg)
    except WebSocketDisconnect:
        pass
    finally:
        streamer.cancel()


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """Tiny built-in test page so the frontend dev can eyeball the stream
    without writing any code first. NOT the real UI — just a sanity check."""
    return """
<!doctype html><html><head><meta charset="utf-8"><title>SIH26052 mock</title>
<style>body{font-family:system-ui;margin:2rem;background:#111;color:#eee}
button{font-size:1rem;padding:.5rem 1rem;margin:.25rem}
#log{white-space:pre-wrap;background:#000;padding:1rem;height:40vh;overflow:auto;
border:1px solid #333;font-family:monospace;font-size:.8rem}</style></head><body>
<h2>SIH26052 mock backend</h2>
<p>This is a fake stream for UI development. Not the real model.</p>
<button onclick="cmd('start')">Start</button>
<button onclick="cmd('stop')">Stop</button>
<button onclick="setModel(true)">Model ON</button>
<button onclick="setModel(false)">Model OFF</button>
<div id="log"></div>
<script>
const log = document.getElementById('log');
const ws = new WebSocket('ws://127.0.0.1:8000/ws');
let n = 0;
ws.onmessage = e => {
  const m = JSON.parse(e.data);
  if (m.type === 'waveform') { n++; if (n % 15 !== 0) return; } // throttle log
  log.textContent = (JSON.stringify(m) + '\\n' + log.textContent).slice(0, 6000);
};
ws.onopen = () => log.textContent = 'connected\\n';
function cmd(a){ ws.send(JSON.stringify({type:'command', action:a})); }
function setModel(on){ ws.send(JSON.stringify({type:'command', action:'set_model', on})); }
</script></body></html>
"""


if __name__ == "__main__":
    print("Mock backend running:")
    print("  test page : http://127.0.0.1:8000/")
    print("  websocket : ws://127.0.0.1:8000/ws")
    uvicorn.run(app, host="127.0.0.1", port=8000)
