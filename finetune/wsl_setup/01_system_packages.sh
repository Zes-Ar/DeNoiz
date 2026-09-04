#!/usr/bin/env bash
# SIH26052 DeNoiz - WSL2 fine-tune setup, stage 1: system packages.
#
# Installs Python 3.11 (via deadsnakes, because Ubuntu 24.04 ships 3.12 which
# is too new for the DeepFilterNet training stack), pip, ffmpeg (audio
# conversion), git, and build tools. Safe to re-run.
#
# Run inside WSL Ubuntu:
#   bash 01_system_packages.sh
set -euo pipefail

echo "==> Ubuntu:"; cat /etc/os-release | grep PRETTY_NAME

echo "==> Updating apt index ..."
sudo apt-get update -y

echo "==> Installing base tools + HDF5 headers (needed to build pyDF-data) ..."
sudo apt-get install -y software-properties-common git ffmpeg build-essential \
    curl pkg-config libhdf5-dev

echo "==> Adding deadsnakes PPA for Python 3.11 ..."
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update -y

echo "==> Installing Python 3.11 + venv + dev headers ..."
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev

echo "==> Versions:"
python3.11 --version
ffmpeg -version | head -n 1
git --version

echo ""
echo "Stage 1 done. Next: bash 02_python_env.sh"
