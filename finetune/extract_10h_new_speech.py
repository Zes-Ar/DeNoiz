"""
SIH26052 DeNoiz - extract 10 MORE hours of completely NEW 48 kHz speech clips
from the VCTK parquet shards, strictly excluding the clips already in speech_48k.

Run inside WSL (venv active):
    python extract_10h_new_speech.py --hours 10.0
"""
from __future__ import annotations

import argparse
import io
import random
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import numpy as np
import soundfile as sf
import pyarrow.parquet as pq
from scipy.signal import resample_poly

SHARD_DIR = Path.home() / "denoiz-finetune" / "data" / "vctk_hf" / "data"
OUT = Path.home() / "denoiz-finetune" / "data" / "speech_48k"
TARGET_SR = 48_000
MIN_SEC = 1.5
MAX_SEC = 12.0
SILENCE_RMS = 1e-3
SEED = 5678


def to_mono(x: np.ndarray) -> np.ndarray:
    return x if x.ndim == 1 else x.mean(axis=1)


def resample_to(x: np.ndarray, sr_in: int) -> np.ndarray:
    if sr_in == TARGET_SR:
        return x
    frac = Fraction(TARGET_SR, sr_in).limit_denominator(1000)
    return resample_poly(x, frac.numerator, frac.denominator)


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x.astype(np.float64) ** 2) + 1e-12))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=10.0)
    args = ap.parse_args()
    target_sec = args.hours * 3600.0

    OUT.mkdir(parents=True, exist_ok=True)
    existing_stems = {p.stem for p in OUT.glob("*.wav")}
    print(f"Found {len(existing_stems)} existing audio clips in {OUT}. These will be strictly skipped.", flush=True)

    shards = sorted(SHARD_DIR.glob("*.parquet"))
    if not shards:
        raise SystemExit(f"No parquet shards in {SHARD_DIR}")

    rng = random.Random(SEED)
    per_shard_sec = target_sec / len(shards)
    print(f"{len(shards)} shards; target {args.hours:.1f} new hours "
          f"(~{per_shard_sec/60:.1f} min/shard) -> {OUT}", flush=True)

    written = 0
    total = 0.0

    for si, shard in enumerate(shards, 1):
        if total >= target_sec:
            break
        tbl = pq.read_table(shard, columns=["audio", "id", "speaker_id"])
        n = tbl.num_rows
        order = list(range(n))
        rng.shuffle(order)

        # group and interleave by speaker
        by_spk = defaultdict(list)
        spk_col = tbl.column("speaker_id")
        id_col = tbl.column("id")
        audio_col = tbl.column("audio")

        for ri in order:
            by_spk[spk_col[ri].as_py()].append(ri)

        interleaved = []
        cursors = {s: 0 for s in by_spk}
        remaining = True
        while remaining:
            remaining = False
            for s, lst in by_spk.items():
                c = cursors[s]
                if c < len(lst):
                    interleaved.append(lst[c])
                    cursors[s] = c + 1
                    remaining = True

        shard_sec = 0.0
        shard_target = per_shard_sec * si - total

        for ri in interleaved:
            if shard_sec >= shard_target and total < target_sec:
                if total + shard_sec >= per_shard_sec * si:
                    break
            if total + shard_sec >= target_sec:
                break

            rid = str(id_col[ri].as_py())
            # Skip clips already present in speech_48k
            if rid in existing_stems:
                continue

            try:
                raw = audio_col[ri].as_py()
                b = raw["bytes"] if isinstance(raw, dict) else raw
                x, sr = sf.read(io.BytesIO(b), dtype="float32", always_2d=False)
            except Exception:
                continue

            x = to_mono(np.asarray(x, dtype=np.float32))
            dur = len(x) / sr
            if dur < MIN_SEC:
                continue
            if dur > MAX_SEC:
                x = x[: int(MAX_SEC * sr)]
            if rms(x) < SILENCE_RMS:
                continue

            x = resample_to(x, sr).astype(np.float32)
            out_file = OUT / f"{rid}.wav"
            sf.write(str(out_file), x, TARGET_SR, subtype="PCM_16")
            existing_stems.add(rid)
            written += 1
            shard_sec += len(x) / TARGET_SR

        total += shard_sec
        print(f"  shard {si:02d}/{len(shards)}: +{shard_sec/60:.1f} min "
              f"(total new: {total/60:.1f} min, {written} new clips)", flush=True)

    print("\n" + "=" * 55, flush=True)
    print(f"New speech clips added: {written}")
    print(f"Total new duration    : {total/3600:.2f} h ({total/60:.1f} min)")
    print(f"Total clips in folder : {len(list(OUT.glob('*.wav')))}")
    print(f"Output directory      : {OUT}")


if __name__ == "__main__":
    main()
