#!/usr/bin/env bash
# Launch stage 3 detached with setsid so it survives session cleanup.
# Logs to ~/denoiz-finetune/stage3.log ; writes stage3.done / stage3.fail.
set -e
DIR="$HOME/denoiz-finetune"
rm -f "$DIR/stage3.done" "$DIR/stage3.fail"
# setsid fully detaches from the controlling terminal so WSL session teardown
# won't kill it; stdbuf keeps the log unbuffered so we can watch progress.
setsid bash -c "stdbuf -oL -eL bash '$DIR/wsl_setup/03_deepfilternet.sh' > '$DIR/stage3.log' 2>&1 && touch '$DIR/stage3.done' || touch '$DIR/stage3.fail'" &
echo "stage 3 launched (setsid), pid $!"
echo "log: $DIR/stage3.log"
