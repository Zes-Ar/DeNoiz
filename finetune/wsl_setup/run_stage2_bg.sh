#!/usr/bin/env bash
# Launch stage 2 detached so it survives the IDE tool timeouts.
# Logs to ~/denoiz-finetune/stage2.log ; writes stage2.done on success.
set -e
DIR="$HOME/denoiz-finetune"
rm -f "$DIR/stage2.done" "$DIR/stage2.fail"
nohup bash -c "bash '$DIR/wsl_setup/02_python_env.sh' && touch '$DIR/stage2.done' || touch '$DIR/stage2.fail'" \
    > "$DIR/stage2.log" 2>&1 &
echo "stage 2 launched in background, pid $!"
echo "log: $DIR/stage2.log"
