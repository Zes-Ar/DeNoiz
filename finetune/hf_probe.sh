#!/usr/bin/env bash
# Install huggingface_hub in the WSL venv and probe VCTK-style datasets:
# list file count and a few sample paths, so we can pick a small-files, resumable source.
set -uo pipefail
source "$HOME/denoiz-finetune/.venv/bin/activate"
pip install -q "huggingface_hub>=0.23" 2>&1 | tail -n 2

python - <<'PY'
from huggingface_hub import HfApi
api = HfApi()
for repo in ["jspaulsen/vctk", "sanchit-gandhi/vctk", "vctk"]:
    try:
        files = api.list_repo_files(repo, repo_type="dataset")
        audio = [f for f in files if f.lower().endswith((".wav", ".flac"))]
        arch  = [f for f in files if f.lower().endswith((".zip", ".tar", ".tgz", ".tar.gz", ".parquet"))]
        print(f"\n=== {repo} ===")
        print(f"  total files: {len(files)}  audio: {len(audio)}  archives/parquet: {len(arch)}")
        for f in (audio[:3] + arch[:3]):
            print("   ", f)
    except Exception as e:
        print(f"\n=== {repo} ===  ERROR: {type(e).__name__}: {e}")
PY
