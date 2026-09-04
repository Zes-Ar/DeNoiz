#!/usr/bin/env bash
# Dry-run: confirm the read_speech part URLs exist and print their sizes.
base="https://dnschallengepublic.blob.core.windows.net/dns5archive/V5_training_dataset/Track1_Headset"
for p in read_speech.tgz.partaa read_speech.tgz.partab read_speech.tgz.partac; do
    echo "== $p =="
    curl -s -I "$base/$p" | grep -iE 'HTTP/|content-length'
done
