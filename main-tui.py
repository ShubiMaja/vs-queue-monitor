#!/usr/bin/env python3
"""
Backward-compatible entry: same as ``python monitor.py --tui``.

Prefer: ``python monitor.py`` (auto GUI or TUI) or ``python monitor.py --tui``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    script = root / "monitor.py"
    argv = [sys.executable, str(script), "--tui"]
    argv.extend(a for a in sys.argv[1:] if a not in ("--tui", "--text"))
    return int(subprocess.call(argv))


if __name__ == "__main__":
    raise SystemExit(main())
