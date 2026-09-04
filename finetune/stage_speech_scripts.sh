#!/usr/bin/env bash
SRC="/mnt/c/Users/arpan/OneDrive/Documents/code/SIH hard/finetune"
DST="$HOME/denoiz-finetune"
mkdir -p "$DST"
for f in get_dns_speech.sh extract_dns_speech.sh; do
    sed 's/\r$//' "$SRC/$f" > "$DST/$f"
    chmod +x "$DST/$f"
done
ls -la "$DST"/get_dns_speech.sh "$DST"/extract_dns_speech.sh
