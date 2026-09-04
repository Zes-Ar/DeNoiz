#!/usr/bin/env bash
# Verify all VCTK parquet shards downloaded and are complete (not truncated).
set -uo pipefail
D="$HOME/denoiz-finetune/data/vctk_hf/data"
echo "==== shard files ===="
ls -lh "$D"/*.parquet 2>/dev/null | tr -d '\r'
echo ""
n=$(ls "$D"/*.parquet 2>/dev/null | wc -l)
echo "parquet shards present: $n (expected 34)"
echo ""
echo "==== total size ===="
du -sh "$HOME/denoiz-finetune/data/vctk_hf" 2>/dev/null | tr -d '\r'
echo ""
echo "==== integrity: can each shard be opened + row counts ===="
source "$HOME/denoiz-finetune/.venv/bin/activate"
python - <<'PY'
from pathlib import Path
import pyarrow.parquet as pq
d = Path.home()/"denoiz-finetune"/"data"/"vctk_hf"/"data"
shards = sorted(d.glob("*.parquet"))
total = 0
bad = []
for f in shards:
    try:
        m = pq.ParquetFile(f).metadata
        total += m.num_rows
    except Exception as e:
        bad.append((f.name, str(e)[:60]))
print(f"openable shards: {len(shards)-len(bad)}/{len(shards)}")
print(f"total clips: {total}")
if bad:
    print("CORRUPT/incomplete shards (re-run the download to fix):")
    for n, e in bad:
        print("  ", n, e)
else:
    print("all shards valid.")
PY
