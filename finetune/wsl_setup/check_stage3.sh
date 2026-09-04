#!/usr/bin/env bash
cd "$HOME/denoiz-finetune"
echo "==== build stages logged ===="
grep -nE "Building pyDF|Building pyDF-data|Installing DeepFilterNet|Cloning|Installing Rust|Installing build deps" stage3.log || true
echo "==== extension imports ===="
source .venv/bin/activate
python -c "import libdf; print('libdf OK')" 2>&1 | tail -n 1
python -c "import libdfdata; print('libdfdata OK')" 2>&1 | tail -n 1
echo "==== tool versions ===="
maturin --version 2>&1 | tail -n 1
echo "PYTHONPATH repo present:"
ls -d "$HOME/denoiz-finetune/DeepFilterNet/DeepFilterNet" 2>&1
