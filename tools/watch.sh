#!/bin/bash
# Polls /workspace/puzzler-out every 120s; validates, ships passing puzzles, then checks the live site.
cd /workspace/crossword
while true; do
  out=$(python3 tools/ingest.py --push 2>&1)
  if echo "$out" | grep -q '^pushed'; then
    echo "$(date) pushed" ; sleep 90
    python3 tools/livecheck.py https://j-grok-bot.github.io/crosser-crossword/ 2>&1 | tail -3
  fi
  sleep 120
done
