#!/usr/bin/env python3
"""
VS Queue Monitor — terminal UI entrypoint (Textual).

Same as: ``python monitor.py --tui``.
"""

from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    script = root / "monitor.py"
    env = dict(os.environ)
    env.setdefault("VS_QUEUE_MONITOR_UI", "tui")
    argv = [sys.executable, str(script), "--tui"]
    argv.extend(a for a in sys.argv[1:] if a not in ("--tui", "--text"))
    return int(subprocess.call(argv, env=env))


if __name__ == "__main__":
    raise SystemExit(main())

