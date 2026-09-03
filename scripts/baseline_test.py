"""
Baseline sanity test for pretrained DeepFilterNet3 on SIH26052 battlefield noise.

Purpose: answer empirically "does the pretrained model actually suppress
battlefield noise, and by how much?" - before committing to any fine-tuning.

Builds synthetic noisy mixtures from the project's own DATASET/ using clean
LibriSpeech speech + real battlefield noise at controlled SNRs, runs the
pretrained model, and reports SI-SDR / SNR improvement.

Writes listenable before/after wavs to out/baseline/.
"""

from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "DATASET"
OUT = ROOT / "out" / "baseline"

TARGET_SR = 48_000  # DeepFilterNet3 operates at 48 kHz
CLIP_SECONDS = 6.0
SNR_LEVELS_DB = [5.0, 0.0, -5.0]
SEED = 1234


# ---------------------------------------------------------------- audio utils

def to_mono(x: np.ndarray) -> np.ndarray:
    return x if x.ndim == 1 else x.mean(axis=1)


def resample_to(x: np.ndarray, sr_in: int, sr_out: int = TARGET_SR) -> np.ndarray:
    if sr_in == sr_out:
        return x
    frac = Fraction(sr_out, sr_in).limit_denominator(1000)
    return resample_poly(x, frac.numerator, frac.denominator)


def read_audio(path: Path) -> np.ndarray:
    """Read any wav/flac -> mono float32 at TARGET_SR."""
    x, sr = sf.read(str(path), dtype="float32", always_2d=False)
    x = to_mono(np.asarray(x, dtype=np.float32))
    return resample_to(x, sr).astype(np.float32)


def fit_length(x: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    """Crop or tile-loop x to exactly n samples."""
    if len(x) == 0:
        return np.zeros(n, dtype=np.float32)
    if len(x) >= n:
        start = 0 if len(x) == n else int(rng.integers(0, len(x) - n))
        return x[start:start + n]
    reps = int(np.ceil(n / len(x)))
    return np.tile(x, reps)[:n]


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x.astype(np.float64) ** 2) + 1e-12))


def mix_at_snr(speech: np.ndarray, noise: np.ndarray, snr_db: float):
    """Scale noise so that mixture hits the requested SNR. Returns (noisy, speech)."""
    s_rms, n_rms = rms(speech), rms(noise)
    if n_rms < 1e-9:
        return speech.copy(), speech
    target_n_rms = s_rms / (10.0 ** (snr_db / 20.0))
    noise = noise * (target_n_rms / n_rms)
    noisy = speech + noise

    # guard against clipping, scaling speech reference identically so SNR holds
    peak = float(np.max(np.abs(noisy))) if noisy.size else 0.0
    if peak > 0.99:
        g = 0.99 / peak
        noisy, speech = noisy * g, speech * g
    return noisy.astype(np.float32), speech.astype(np.float32)


# ------------------------------------------------------------------- metrics

def si_sdr_db(est: np.ndarray, ref: np.ndarray) -> float:
    """Scale-invariant SDR. Higher is better."""
    n = min(len(est), len(ref))
    est, ref = est[:n].astype(np.float64), ref[:n].astype(np.float64)
    est = est - est.mean()
    ref = ref - ref.mean()
    denom = np.dot(ref, ref) + 1e-12
    proj = (np.dot(est, ref) / denom) * ref
    noise = est - proj
    return float(10.0 * np.log10((np.dot(proj, proj) + 1e-12) / (np.dot(noise, noise) + 1e-12)))


def align(est: np.ndarray, ref: np.ndarray):
    n = min(len(est), len(ref))
    return est[:n], ref[:n]


# ------------------------------------------------------- dataset file pickers

def pick_speech(rng: np.random.Generator, k: int) -> list[Path]:
    root = DATA / "LibriSpeech"
    files = sorted(root.rglob("*.flac"))
    if not files:
        sys.exit(f"No LibriSpeech .flac found under {root}")
    idx = rng.choice(len(files), size=min(k, len(files)), replace=False)
    return [files[int(i)] for i in idx]


def pick_noise_sources(rng: np.random.Generator) -> dict[str, Path]:
    """One representative file per battlefield noise category."""
    chosen: dict[str, Path] = {}

    def first_random(files: list[Path], label: str, min_sec: float = 0.0):
        files = [f for f in files if f.is_file()]
        if not files:
            return
        rng.shuffle(files)
        for f in files[:40]:
            try:
                info = sf.info(str(f))
                if info.frames / info.samplerate >= min_sec:
                    chosen[label] = f
                    return
            except Exception:
                continue

    # Gunfire - impulsive (edge-collected, 44.1 kHz)
    first_random(list((DATA / "edge-collected-gunshot-audio").rglob("*.wav")),
                 "gunfire", min_sec=2.0)

    # Helicopter - continuous. MAD label 5 (inferred from YouTube titles).
    heli = list((DATA / "helicopter_noise").rglob("*.wav"))
    first_random(heli, "helicopter", min_sec=3.0)
    if "helicopter" not in chosen:
        first_random(_mad_files_for_label(5), "helicopter", min_sec=3.0)

    # Jet aircraft - continuous. MAD label 6.
    first_random(_mad_files_for_label(6), "jet_aircraft", min_sec=3.0)

    # Tank / artillery - MAD labels 3,4
    first_random(_mad_files_for_label(3) + _mad_files_for_label(4),
                 "tank_artillery", min_sec=3.0)

    # Continuous machine/vehicle noise from NOISEX-92 etc.
    first_random(list((DATA / "Noises-master").rglob("*.wav")),
                 "noisex_continuous", min_sec=3.0)

    return chosen


_mad_cache: dict[int, list[Path]] | None = None


def _mad_files_for_label(label: int) -> list[Path]:
    """Resolve MAD clips for a numeric label using training.csv."""
    global _mad_cache
    if _mad_cache is None:
        _mad_cache = {}
        csv_path = DATA / "MAD_dataset" / "training.csv"
        if csv_path.exists():
            import csv as _csv
            with open(csv_path, newline="", encoding="utf-8", errors="replace") as fh:
                for row in _csv.DictReader(fh):
                    rel, lab = row.get("path"), row.get("label")
                    if not rel or lab is None:
                        continue
                    try:
                        lab_i = int(lab)
                    except ValueError:
                        continue
                    p = DATA / "MAD_dataset" / rel.replace("/", "\\")
                    _mad_cache.setdefault(lab_i, []).append(p)
    return list(_mad_cache.get(label, []))


# ----------------------------------------------------------------------- main

def main() -> None:
    rng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    print("Loading pretrained DeepFilterNet3 ...")
    from df.enhance import enhance, init_df
    import torch

    model, df_state, _ = init_df(config_allow_defaults=True)
    model_sr = df_state.sr()
    print(f"  model ready, sample rate = {model_sr} Hz")
    if model_sr != TARGET_SR:
        print(f"  NOTE: model sr {model_sr} != assumed {TARGET_SR}")

    noise_sources = pick_noise_sources(rng)
    if not noise_sources:
        sys.exit("No noise files resolved from DATASET/")

    print("\nNoise categories selected:")
    for label, path in noise_sources.items():
        print(f"  {label:<20} {path.relative_to(DATA)}")

    speech_files = pick_speech(rng, k=len(noise_sources) * len(SNR_LEVELS_DB))
    n_samples = int(CLIP_SECONDS * TARGET_SR)

    rows: list[tuple[str, float, float, float, float]] = []
    sp_iter = iter(speech_files)

    print(f"\nRunning {len(noise_sources) * len(SNR_LEVELS_DB)} mixtures "
          f"({CLIP_SECONDS:.0f}s each) ...\n")

    for label, npath in noise_sources.items():
        noise_full = read_audio(npath)
        for snr in SNR_LEVELS_DB:
            spath = next(sp_iter)
            speech = fit_length(read_audio(spath), n_samples, rng)
            noise = fit_length(noise_full, n_samples, rng)

            noisy, speech_ref = mix_at_snr(speech, noise, snr)

            audio_t = torch.from_numpy(noisy).unsqueeze(0)
            enhanced = enhance(model, df_state, audio_t).squeeze(0).numpy()

            e, r = align(enhanced, speech_ref)
            nz, _ = align(noisy, speech_ref)

            before = si_sdr_db(nz, r)
            after = si_sdr_db(e, r)
            rows.append((label, snr, before, after, after - before))

            tag = f"{label}_snr{int(snr):+d}dB"
            sf.write(str(OUT / f"{tag}_1_noisy.wav"), nz, TARGET_SR)
            sf.write(str(OUT / f"{tag}_2_enhanced.wav"), e, TARGET_SR)
            sf.write(str(OUT / f"{tag}_0_clean.wav"), r, TARGET_SR)

            print(f"  {label:<20} SNR {snr:+5.1f} dB   "
                  f"SI-SDR {before:6.2f} -> {after:6.2f}   "
                  f"(delta {after - before:+5.2f} dB)")

    # ------------------------------------------------------------- summary
    print("\n" + "=" * 78)
    print("BASELINE RESULTS - pretrained DeepFilterNet3, no fine-tuning")
    print("=" * 78)
    print(f"{'noise category':<20} {'mix SNR':>8} {'SI-SDR in':>10} "
          f"{'SI-SDR out':>11} {'improvement':>12}")
    print("-" * 78)
    for label, snr, before, after, delta in rows:
        print(f"{label:<20} {snr:+7.1f}  {before:10.2f} {after:11.2f} {delta:+11.2f}")
    print("-" * 78)

    deltas = [d for *_, d in rows]
    print(f"{'MEAN':<20} {'':>8} {'':>10} {'':>11} {np.mean(deltas):+11.2f}")

    print("\nPer-category mean improvement:")
    for label in noise_sources:
        d = [x[4] for x in rows if x[0] == label]
        print(f"  {label:<20} {np.mean(d):+6.2f} dB")

    print(f"\nListenable wavs written to: {OUT}")
    print("  *_0_clean.wav / *_1_noisy.wav / *_2_enhanced.wav")


if __name__ == "__main__":
    main()
