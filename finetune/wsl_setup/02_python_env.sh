#!/usr/bin/env bash
# SIH26052 DeNoiz - WSL2 fine-tune setup, stage 2: venv + CUDA PyTorch.
#
# Creates a dedicated Python 3.11 venv in the Linux filesystem (fast), installs
# a CUDA-enabled PyTorch matched to your RTX 4060, and verifies the GPU is
# visible to torch. Does NOT install DeepFilterNet yet - we confirm CUDA first.
#
# Run inside WSL Ubuntu:
#   bash 02_python_env.sh
set -euo pipefail

PROJECT="$HOME/denoiz-finetune"
VENV="$PROJECT/.venv"

echo "==> Project dir: $PROJECT"
mkdir -p "$PROJECT"

echo "==> Creating venv at $VENV (python3.11) ..."
python3.11 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "==> Upgrading pip ..."
python -m pip install --upgrade pip wheel setuptools

# CUDA 12.1 build of PyTorch works with the 596.x / CUDA 13.x driver via WSL.
# (Driver is backward compatible; we pin a torch that DeepFilterNet trains on.)
echo "==> Installing CUDA-enabled PyTorch (this downloads a few GB) ..."
pip install --progress-bar off torch==2.1.2 torchaudio==2.1.2 \
    --index-url https://download.pytorch.org/whl/cu121

echo "==> Verifying GPU is visible to PyTorch ..."
python - <<'PY'
import torch
print("torch          :", torch.__version__)
print("cuda available :", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device         :", torch.cuda.get_device_name(0))
    print("capability     :", torch.cuda.get_device_capability(0))
    x = torch.randn(1024, 1024, device="cuda")
    y = (x @ x).sum().item()
    print("gpu matmul ok  :", isinstance(y, float))
else:
    raise SystemExit("!! CUDA not visible to torch - stop and debug before continuing.")
PY

echo ""
echo "Stage 2 done. GPU works with PyTorch. Next: bash 03_deepfilternet.sh"
