"""
Find the smallest audio block size that DeepFilterNet3 can process in real time
on this machine, using the high-level enhance() API.

Why this matters: enhance() has significant fixed per-call overhead, so calling
it once per 10 ms frame is far slower than real time even though the model
itself is fast. Processing in larger blocks amortises that overhead.

Trade-off: bigger block = safer real-time margin, but more input latency.
Total demo latency is roughly (block size + ~40 ms model latency + I/O buffers).
"""

import time

import numpy as np
import torch

from df.enhance import enhance, init_df

SR = 48_000
BLOCK_MS = [10, 20, 40, 60, 80, 100, 160, 200, 320, 500, 1000]
TEST_SECONDS = 4.0
SAFE_RTF = 0.5  # want compute to use at most half the available time


def main() -> None:
    model, df_state, _ = init_df(config_allow_defaults=True)
    print(f"model sr={df_state.sr()} Hz  torch_threads={torch.get_num_threads()}\n")

    rng = np.random.default_rng(0)

    print(f"{'block':>8} {'calls':>7} {'mean/call':>11} {'RTF':>7} "
          f"{'x realtime':>11}  verdict")
    print("-" * 66)

    results = []
    for bms in BLOCK_MS:
        n = int(SR * bms / 1000)
        calls = max(3, int(TEST_SECONDS * 1000 / bms))

        # warm up
        for _ in range(3):
            w = rng.normal(0, 0.05, n).astype(np.float32)
            enhance(model, df_state, torch.from_numpy(w).unsqueeze(0))

        times = []
        for _ in range(calls):
            chunk = rng.normal(0, 0.05, n).astype(np.float32)
            t = torch.from_numpy(chunk).unsqueeze(0)
            t0 = time.perf_counter()
            enhance(model, df_state, t)
            times.append(time.perf_counter() - t0)

        arr = np.array(times)
        mean_ms = arr.mean() * 1000
        rtf = mean_ms / bms

        if rtf <= SAFE_RTF:
            verdict = "SAFE"
        elif rtf < 1.0:
            verdict = "tight"
        else:
            verdict = "TOO SLOW"

        results.append((bms, rtf, mean_ms, verdict))
        print(f"{bms:>6} ms {calls:>7} {mean_ms:>9.2f} ms {rtf:>7.3f} "
              f"{1 / rtf:>10.1f}x  {verdict}")

    print("-" * 66)

    safe = [r for r in results if r[3] == "SAFE"]
    if safe:
        bms, rtf, mean_ms, _ = safe[0]
        est_latency = bms + 40  # block + model algorithmic latency
        print(f"\nRECOMMENDED block size: {bms} ms")
        print(f"  compute {mean_ms:.1f} ms per {bms} ms block  (RTF {rtf:.3f}, "
              f"{1 / rtf:.1f}x real-time headroom)")
        print(f"  estimated end-to-end latency ~= {est_latency} ms "
              f"({bms} ms block + ~40 ms model)")
        print("  plus audio I/O buffering on top")
    else:
        print("\nNo block size hit the SAFE threshold - consider the ONNX / "
              "Rust streaming path instead of the Python enhance() API.")


if __name__ == "__main__":
    main()
