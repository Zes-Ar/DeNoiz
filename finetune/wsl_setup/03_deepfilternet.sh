#!/usr/bin/env bash
# SIH26052 DeNoiz - WSL2 fine-tune setup, stage 3: DeepFilterNet training stack.
#
# Installs the Rust toolchain, clones the DeepFilterNet repo, installs its
# Python deps via poetry, and BUILDS the two Rust extensions:
#   pyDF       - STFT/ISTFT processing loop (needed by enhance/train)
#   pyDF-data  - the HDF5 pytorch dataloader  (THE Linux-only training piece)
#
# Follows the official manual-install steps from the DeepFilterNet README.
# Assumes stage 1 (system pkgs incl. libhdf5-dev) and stage 2 (venv + torch)
# have completed. Safe to re-run.
#
# Run inside WSL Ubuntu:
#   bash 03_deepfilternet.sh
set -euo pipefail

PROJECT="$HOME/denoiz-finetune"
VENV="$PROJECT/.venv"
REPO="$PROJECT/DeepFilterNet"

# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "==> Installing Rust toolchain (rustup) if missing ..."
if ! command -v cargo >/dev/null 2>&1; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
fi
# shellcheck disable=SC1091
source "$HOME/.cargo/env"
cargo --version

echo "==> Cloning DeepFilterNet repo ..."
if [ ! -d "$REPO/.git" ]; then
    git clone https://github.com/Rikorose/DeepFilterNet.git "$REPO"
fi
cd "$REPO"
echo "    repo at: $REPO  (commit $(git rev-parse --short HEAD))"

echo "==> Installing build deps (maturin, poetry) + dataset-prep deps ..."
pip install maturin poetry
pip install h5py librosa soundfile

echo "==> Installing DeepFilterNet python deps (train + eval extras, no-root) ..."
# --no-root: use the repo version directly (Option B in the README)
poetry -C DeepFilterNet install -E train -E eval --no-root
export PYTHONPATH="$REPO/DeepFilterNet"

echo "==> Building pyDF (STFT/ISTFT) ..."
maturin develop --release -m pyDF/Cargo.toml

echo "==> Building pyDF-data (HDF5 dataloader - the training-only piece) ..."
# If plain build fails on HDF5 linking, fall back to static hdf5.
if ! maturin develop --release -m pyDF-data/Cargo.toml; then
    echo "    plain HDF5 build failed; retrying with --features hdf5-static ..."
    maturin develop --release --features hdf5-static -m pyDF-data/Cargo.toml
fi

echo "==> Verifying imports ..."
python - <<'PY'
import importlib
for mod in ("torch", "df", "libdf", "libdfdata"):
    try:
        m = importlib.import_module(mod)
        print(f"  {mod:10s} OK")
    except Exception as e:
        print(f"  {mod:10s} FAIL -> {e}")
import torch
print("  cuda available:", torch.cuda.is_available())
PY

echo ""
echo "Stage 3 done. If all four imports say OK and cuda=True, the training"
echo "environment is ready. Next we prepare data into HDF5 and launch train.py."
echo "PYTHONPATH must be set in each new shell:  export PYTHONPATH=$REPO/DeepFilterNet"
