#!/usr/bin/env bash
# Diagnose whether the Azure blob supports HTTP range requests (resume).
url="https://dnschallengepublic.blob.core.windows.net/dns5archive/V5_training_dataset/Track1_Headset/read_speech.tgz.partaa"

echo "==== plain HEAD ===="
curl -s -I "$url" | grep -iE 'HTTP/|accept-ranges|content-length' | tr -d '\r'

echo "==== ranged GET (bytes=0-100) : does it return 206 Partial? ===="
curl -s -I -H "Range: bytes=0-100" "$url" | grep -iE 'HTTP/|content-range|content-length|accept-ranges' | tr -d '\r'
