#!/bin/bash
# Serial render queue: renders story ids appended to $Q (one per line) one after another, one ComfyUI job at a time.
# Stops when $Q.stop exists and the queue is drained, or at WEBTOON_DEADLINE (exit 3, resume later).
#   Q=out/romance/queue.txt WEBTOON_DEADLINE=12:55 m0/run_queue.sh
set -u
cd "$(dirname "$0")/.."
Q="${Q:-out/romance/queue.txt}"; touch "$Q" "$Q.done"
while pgrep -f run_matrix.sh >/dev/null; do sleep 15; done
while true; do
  s=$(grep -vxF -f "$Q.done" "$Q" | head -1)
  if [ -z "$s" ]; then [ -e "$Q.stop" ] && break; sleep 15; continue; fi
  m0/run_romance.sh "$s"; rc=$?
  [ $rc -eq 3 ] && exit 3
  echo "$s" >> "$Q.done"
done
echo "== queue done $(date +%H:%M)"
