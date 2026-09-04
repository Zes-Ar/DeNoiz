#!/usr/bin/env bash
# Does the Edinburgh DataShare VCTK zip support HTTP range resume?
url="https://datashare.ed.ac.uk/bitstream/handle/10283/3443/VCTK-Corpus-0.92.zip"
alt="https://datashare.is.ed.ac.uk/bitstream/handle/10283/3443/VCTK-Corpus-0.92.zip"

for u in "$url" "$alt"; do
  echo "==== $u ===="
  echo "-- plain HEAD --"
  curl -sIL "$u" | grep -iE 'HTTP/|accept-ranges|content-length|location' | tr -d '\r'
  echo "-- ranged (bytes=0-100), want 206 --"
  curl -sIL -H "Range: bytes=0-100" "$u" | grep -iE 'HTTP/|content-range|accept-ranges' | tr -d '\r'
  echo ""
done
