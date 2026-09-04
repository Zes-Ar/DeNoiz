#!/usr/bin/env bash
# SIH26052 DeNoiz - extract the downloaded DNS-5 read_speech parts.
#
# The parts are pieces of ONE split .tar.gz. We concatenate them and extract.
# Because we only grabbed 3 of ~21 parts, the archive is TRUNCATED: tar will
# extract every complete file and then report an error on the final, cut-off
# file. That trailing error is EXPECTED and harmless - all whole files are out.
set -uo pipefail

RAW="$HOME/denoiz-finetune/data/dns_speech_raw"
OUT="$HOME/denoiz-finetune/data/dns_speech"
mkdir -p "$OUT"
cd "$RAW"

echo "==> Concatenating parts into one stream and extracting to $OUT ..."
# Stream the joined parts through tar. Ignore tar's expected 'unexpected EOF'
# from the truncated last part.
cat read_speech.tgz.parta* | tar -xz -C "$OUT" 2>/tmp/dns_tar_err || true

echo "==> Extraction finished (trailing EOF error is expected)."
echo "    tar stderr (last lines):"
tail -n 3 /tmp/dns_tar_err 2>/dev/null || true

echo ""
echo "==> Counting extracted 48 kHz speech files ..."
n=$(find "$OUT" -type f -name '*.wav' | wc -l)
echo "    wav files: $n"
echo "    sample (first 3):"
find "$OUT" -type f -name '*.wav' | head -n 3

echo ""
echo "Done. Speech is in: $OUT"
