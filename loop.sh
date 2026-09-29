#!/usr/bin/env bash
# Huncho Trader paper cycle: screen markets, paper-log, settle, score.
# Paper only. Never places orders. See REAL.md before enabling real money.
set -euo pipefail
cd "$(dirname "$0")"

if [ "${1:-}" = "--real" ]; then
  echo "Real execution is operator-only and disabled by default. See REAL.md."
  exit 1
fi

if [ "${1:-}" = "--watch" ]; then
  every="${2:-15}"
  echo "Paper watch: cycling every ${every} minutes. Ctrl-C to stop."
  while true; do
    python3 core/screen.py
    python3 core/score.py | head -20
    echo "--- sleeping ${every}m ---"
    sleep "${every}m"
  done
  exit 0
fi

python3 core/screen.py
python3 core/score.py
