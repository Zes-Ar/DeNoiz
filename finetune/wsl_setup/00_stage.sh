#!/usr/bin/env bash
# Copy the setup scripts from the Windows mount into the WSL home and strip CRLF.
set -e
SRC="/mnt/c/Users/arpan/OneDrive/Documents/code/SIH hard/finetune/wsl_setup"
DST="$HOME/denoiz-finetune/wsl_setup"
mkdir -p "$DST"
for f in "$SRC"/*.sh; do
    base=$(basename "$f")
    sed 's/\r$//' "$f" > "$DST/$base"
    chmod +x "$DST/$base"
done
echo "Copied to $DST :"
ls -la "$DST"
