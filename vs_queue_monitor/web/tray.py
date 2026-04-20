"""System-tray presence for VS Queue Monitor.

Optional: requires ``pystray`` (and ``Pillow`` for the icon image).
If either is missing, ``start_tray`` is a silent no-op — the app still works.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path


def _load_icon_image():
    """Return a PIL RGBA Image for the tray icon, or None."""
    try:
        from PIL import Image

        assets_gif = Path(__file__).parent.parent.parent / "assets" / "app_icon.gif"
        if assets_gif.exists():
            img = Image.open(str(assets_gif))
            img = img.convert("RGBA")
            return img

        # Programmatic fallback: dark square with a blue "V" accent
        from PIL import ImageDraw

        size = 64
        img = Image.new("RGBA", (size, size), (30, 35, 41, 255))
        draw = ImageDraw.Draw(img)
        mid = size // 2
        draw.polygon(
            [
                (10, 14), (mid, size - 10), (size - 10, 14),
                (size - 18, 14), (mid, size - 22), (18, 14),
            ],
            fill=(87, 148, 242, 255),
        )
        return img
    except Exception:
        return None


def start_tray(url: str) -> None:
    """Show a system-tray icon that links to the running web UI.

    Spawns a daemon thread; returns immediately.
    Silent no-op when ``pystray`` is not installed.
    """
    try:
        import pystray
    except ImportError:
        return

    icon_image = _load_icon_image()
    if icon_image is None:
        return

    import webbrowser

    def _open(_icon=None, _item=None) -> None:
        webbrowser.open(url)

    def _quit(icon, _item=None) -> None:
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Open VS Queue Monitor", _open, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", _quit),
    )
    icon = pystray.Icon("vs-queue-monitor", icon_image, "VS Queue Monitor", menu)

    # run_detached() (pystray >= 0.19) manages its own thread; fall back to daemon thread.
    try:
        icon.run_detached()
    except AttributeError:
        threading.Thread(target=icon.run, daemon=True, name="vs-queue-monitor-tray").start()
