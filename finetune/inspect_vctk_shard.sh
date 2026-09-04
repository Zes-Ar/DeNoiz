#!/usr/bin/env bash
# Download ONE VCTK parquet shard and inspect its structure + sample rate,
# so we confirm the extraction approach before pulling all 34 shards.
set -uo pipefail
source "$HOME/denoiz-finetune/.venv/bin/activate"
pip install -q "huggingface_hub>=0.23" pyarrow 2>&1 | tail -n 1

python - <<'PY'
from huggingface_hub import hf_hub_download
from pathlib import Path
import pyarrow.parquet as pq

dest = Path.home()/"denoiz-finetune"/"data"/"vctk_hf"
dest.mkdir(parents=True, exist_ok=True)
f = hf_hub_download("jspaulsen/vctk", "data/train-00000-of-00034.parquet",
                    repo_type="dataset", local_dir=str(dest))
print("downloaded:", f)

pf = pq.ParquetFile(f)
print("rows:", pf.metadata.num_rows)
print("columns:", pf.schema.names)
# peek one row
tbl = pf.read_row_group(0)
row0 = {c: tbl.column(c)[0] for c in tbl.column_names}
for c, v in row0.items():
    s = str(v)
    print(f"  {c}: {s[:120]}")
PY
