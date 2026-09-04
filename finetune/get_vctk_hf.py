"""
SIH26052 DeNoiz - download 48 kHz clean SPEECH (VCTK) from the Hugging Face Hub.

Why this instead of the DNS Azure link: the DNS blob server refuses HTTP range
requests, so a dropped connection cannot resume a 5 GB file. VCTK on HF is
stored as ~34 small parquet shards (~330 MB each) and hf_hub_download RESUMES
automatically and SKIPS shards already complete. Small files + resume = robust
on a flaky ~1 MB/s link. VCTK is 48 kHz, 110 English speakers (accent diverse).

Run inside WSL Ubuntu (venv active or via the wrapper script):
    python get_vctk_hf.py            # download all shards (resumable)
    python get_vctk_hf.py --shards 12   # only first 12 shards (~4 GB) if you want less

Re-run any time; completed shards are skipped, partial ones resume.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download

REPO = "jspaulsen/vctk"
DEST = Path.home() / "denoiz-finetune" / "data" / "vctk_hf"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", type=int, default=0,
                    help="limit to first N parquet shards (0 = all)")
    args = ap.parse_args()

    DEST.mkdir(parents=True, exist_ok=True)
    # resume behaviour is on by default in recent hf_hub; be explicit anyway
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")

    api = HfApi()
    files = api.list_repo_files(REPO, repo_type="dataset")
    shards = sorted(f for f in files if f.endswith(".parquet"))
    if args.shards > 0:
        shards = shards[:args.shards]
    print(f"Repo {REPO}: downloading {len(shards)} parquet shard(s) to {DEST}")
    print("Resumable + skips completed. Re-run if the connection drops.\n")

    for i, f in enumerate(shards, 1):
        print(f"[{i}/{len(shards)}] {f}")
        for attempt in range(1, 1000):
            try:
                hf_hub_download(
                    repo_id=REPO, filename=f, repo_type="dataset",
                    local_dir=str(DEST),
                    # local_dir_use_symlinks removed in newer hub; safe to omit
                )
                break
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"    retry {attempt}: {type(e).__name__}: {e}")
                import time
                time.sleep(10)
        print("    ok")

    print("\nAll requested shards present in:", DEST)
    print("Next: extract wavs with extract_vctk_parquet.py")


if __name__ == "__main__":
    main()
