#!/usr/bin/env bash
# Verify the WSL venv's PyTorch sees the RTX 4060.
set -e
source "$HOME/denoiz-finetune/.venv/bin/activate"
python - <<'PY'
import torch
print("torch          :", torch.__version__)
print("cuda available :", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device         :", torch.cuda.get_device_name(0))
    print("capability     :", torch.cuda.get_device_capability(0))
    x = torch.randn(2048, 2048, device="cuda")
    y = (x @ x).sum().item()
    print("gpu matmul ok  :", isinstance(y, float))
else:
    print("!! CUDA NOT visible to torch")
PY
