"""
Real-time capability check for DeepFilterNet3 on this machine (CPU).

Answers: can this laptop run the model faster than audio arrives?
Reports the real-time factor (RTF). RTF < 1.0 means real-time is possible;
RTF around 0.1 means ~10x faster than real-time (comfortable headroom).
"""

import time

import numpy as np
import torch

from df.enhance import enhance, init_df

SR = 48_000
HOP_MS = 10.0           # DeepFilterNet3 hop size
CHUNK_SAMPLES = int(SR * HOP_MS / 1000)
N_CHUNKS = 500          # ~5 seconds of audio, frame by frame


def main() -> None:
    torch.set_num_threads(max(1, (torch.get_num_threads() or 4)))
    model, df_state, _ = init_df(config_allow_defaults=True)
    print(f"model sr = {df_state.sr()} Hz, torch threads = {torch.get_num_threads()}")

    rng = np.random.default_rng(0)

    # ---- streaming-style: one hop-sized chunk at a time (worst case per-frame)
    print(f"\nStreaming test: {N_CHUNKS} chunks of {HOP_MS:.0f} ms "
          f"({CHUNK_SAMPLES} samples each)")

    # warm up so lazy init / caches don't pollute timings
    for _ in range(20):
        warm = rng.normal(0, 0.05, CHUNK_SAMPLES).astype(np.float32)
        enhance(model, df_state, torch.from_numpy(warm).unsqueeze(0))

    latencies_ms = []
    for _ in range(N_CHUNKS):
        chunk = rng.normal(0, 0.05, CHUNK_SAMPLES).astype(np.float32)
        t = torch.from_numpy(chunk).unsqueeze(0)
        t0 = time.perf_counter()
        enhance(model, df_state, t)
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)

    lat = np.array(latencies_ms)
    audio_ms = N_CHUNKS * HOP_MS
    compute_ms = lat.sum()
    rtf = compute_ms / audio_ms

    print(f"  audio processed     : {audio_ms / 1000:.2f} s")
    print(f"  compute time        : {compute_ms / 1000:.2f} s")
    print(f"  REAL-TIME FACTOR    : {rtf:.3f}   "
          f"({'OK - ' + format(1 / rtf, '.1f') + 'x faster than real-time' if rtf < 1 else 'TOO SLOW'})")
    print(f"  per-chunk mean      : {lat.mean():.2f} ms  (budget {HOP_MS:.0f} ms)")
    print(f"  per-chunk median    : {np.median(lat):.2f} ms")
    print(f"  per-chunk p95       : {np.percentile(lat, 95):.2f} ms")
    print(f"  per-chunk max       : {lat.max():.2f} ms")
    over = int((lat > HOP_MS).sum())
    print(f"  chunks over budget  : {over}/{N_CHUNKS} ({100 * over / N_CHUNKS:.1f}%)")

    # ---- batch test: process a longer block at once (what the offline demo does)
    print("\nBatch test: 10 s clip processed in one call")
    block = rng.normal(0, 0.05, SR * 10).astype(np.float32)
    t = torch.from_numpy(block).unsqueeze(0)
    t0 = time.perf_counter()
    enhance(model, df_state, t)
    el = time.perf_counter() - t0
    print(f"  10.00 s audio in {el:.2f} s  ->  RTF {el / 10:.3f} "
          f"({1 / (el / 10):.1f}x real-time)")

    print("\nAlgorithmic latency (inherent to the model, not compute):")
    print(f"  frame hop {HOP_MS:.0f} ms + DF lookahead -> ~40 ms inherent")
    print("  add audio I/O buffering on top for true end-to-end latency")


if __name__ == "__main__":
    main()
