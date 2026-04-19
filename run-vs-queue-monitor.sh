#!/usr/bin/env sh
# From the repo root: chmod +x run-vs-queue-monitor.sh  (once)
# Then double-click may work in your file manager, or run: ./run-vs-queue-monitor.sh
cd "$(dirname "$0")" || exit 1
if [ -x ".venv/bin/python" ]; then
  exec ".venv/bin/python" monitor.py "$@"
else
  exec python3 monitor.py "$@"
fi
