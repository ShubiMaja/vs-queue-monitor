#!/usr/bin/env python3
"""
VS Queue Monitor - Vintage Story client log queue monitor (project id: vs-queue-monitor).
Version: 1.1.147

Cross-platform app that watches a Vintage Story client log for queue
position changes and raises configurable threshold alerts (popup + sound).

This file is a thin entrypoint; implementation lives in the ``vs_queue_monitor`` package.
For a single downloaded file that clones (if needed), creates a venv, installs deps, and
starts the app, use ``bootstrap.py`` in the repo (see README Quick start).

WARNING - WORK IN PROGRESS: Behavior, UI, and saved settings may change without notice.

WARNING - AI-ASSISTED DEVELOPMENT: Much of this codebase was produced or refactored with
AI / coding assistants. Treat paths, alerts, ETAs, and log interpretation as unverified
until you confirm them against your client and logs.

WARNING - NO WARRANTY: Not affiliated with Vintage Story. Use at your own risk.
"""

from vs_queue_monitor.cli import main

# Re-export for tests and ``import monitor`` compatibility
from vs_queue_monitor import APP_DISPLAY_NAME, GITHUB_REPO_URL  # noqa: E402


def _show_startup_error() -> None:
    """Show a GUI popup with the current exception traceback, then print to stderr."""
    import sys
    import traceback

    tb = traceback.format_exc()
    print(tb, file=sys.stderr, flush=True)

    title = "VS Queue Monitor - failed to start"
    # Trim to a sane length for the dialog body.
    body = tb if len(tb) <= 1800 else "..." + tb[-1800:]

    try:
        import tkinter
        import tkinter.messagebox

        root = tkinter.Tk()
        root.withdraw()
        tkinter.messagebox.showerror(title, body)
        root.destroy()
        return
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, body, title, 0x10)  # MB_ICONERROR
        except Exception:
            pass


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        raise SystemExit(0)
    except Exception:
        _show_startup_error()
        raise SystemExit(1)
