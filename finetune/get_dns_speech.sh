#!/usr/bin/env bash
# SIH26052 DeNoiz - download 48 kHz clean SPEECH for fine-tuning.
#
# Grabs 3 parts of DNS-5 Track1 read_speech (real spoken speech, 48 kHz, many
# speakers). Each part is 5 GB -> 15 GB total. RESUMABLE: if the connection
# drops, just re-run this script; curl -C - continues where it left off.
#
# Run inside WSL Ubuntu:
#   bash get_dns_speech.sh
#
# After all 3 parts finish, run the companion extractor: extract_dns_speech.sh
set -uo pipefail

BASE="https://dnschallengepublic.blob.core.windows.net/dns5archive/V5_training_dataset/Track1_Headset"
DEST="$HOME/denoiz-finetune/data/dns_speech_raw"
PARTS=(read_speech.tgz.partaa read_speech.tgz.partab read_speech.tgz.partac)

mkdir -p "$DEST"
cd "$DEST"

echo "Downloading ${#PARTS[@]} parts (5 GB each) to: $DEST"
echo "Resumable: re-run this script if it drops. Ctrl-C to pause."
echo ""

for p in "${PARTS[@]}"; do
    echo "==> $p"
    # -C - : resume; --retry: auto-retry on transient errors; -L: follow redirects
    curl -L -C - --retry 20 --retry-delay 10 --retry-all-errors \
        "$BASE/$p" -o "$p"
    echo "    done: $(du -h "$p" | cut -f1)"
done

echo ""
echo "All parts downloaded. Sizes:"
ls -lh "$DEST"/read_speech.tgz.part*
echo ""
echo "Next: bash extract_dns_speech.sh"
