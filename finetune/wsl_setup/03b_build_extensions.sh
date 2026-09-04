#!/usr/bin/env bash
# SIH26052 DeNoiz - stage 3b: finish the two Rust extension builds.
#
# Stage 3 completed Rust + repo + poetry deps but the isolated maturin build
# of pyDF-data timed out downloading maturin on a slow link. Fix: build with
# --no-build-isolation so it reuses the already-installed maturin, and give pip
# a long network timeout for any dependency fetches during the build.
set -euo pipefail

PROJECT="$HOME/denoiz-finetune"
REPO="$PROJECT/DeepFilterNet"
export PYTHONPATH="$REPO/DeepFilterNet"

# long timeouts + retries for the slow connection
export PIP_DEFAULT_TIMEOUT=120
export PIP_RETRIES=10

# shellcheck disable=SC1091
source "$PROJECT/.venv/bin/activate"
# shellcheck disable=SC1091
source "$HOME/.cargo/env"

cd "$REPO"
echo "==> maturin: $(maturin --version)   cargo: $(cargo --version)"

echo "==> Building pyDF (STFT/ISTFT) ..."
maturin develop --release -m pyDF/Cargo.toml

echo "==> Building pyDF-data (HDF5 dataloader) ..."
if ! maturin develop --release -m pyDF-data/Cargo.toml; then
    echo "   plain HDF5 build failed; retrying with --features hdf5-static ..."
    maturin develop --release --features hdf5-static -m pyDF-data/Cargo.toml
fi

echo "==> Verifying imports ..."
python - <<'PY'
import importlib
ok = True
for mod in ("torch", "df", "libdf", "libdfdata"):
    try:
        importlib.import_module(mod)
        print(f"  {mod:10s} OK")
    except Exception as e:
        ok = False
        print(f"  {mod:10s} FAIL -> {e}")
import torch
print("  cuda available:", torch.cuda.is_available())
raise SystemExit(0 if ok else 1)
PY

echo ""
echo "Stage 3b done. Training environment is ready."
