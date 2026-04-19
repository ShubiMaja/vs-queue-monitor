"""Native OS notifications from the Python process.

The embedded web UI (pywebview / WebView2) often does not surface the Web
Notifications API as real system toasts. Threshold and completion alerts call
:func:`try_notify` so users still get OS-level notifications when
``plyer`` is available.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_plyer_import_ok: Optional[bool] = None


def plyer_notification_available() -> bool:
    """True if ``plyer.facades.notification`` can be imported."""
    global _plyer_import_ok
    if _plyer_import_ok is not None:
        return _plyer_import_ok
    try:
        from plyer import notification  # noqa: F401

        _plyer_import_ok = True
    except Exception:
        _plyer_import_ok = False
    return _plyer_import_ok


def try_notify(title: str, message: str, *, app_name: str = "VS Queue Monitor") -> bool:
    """Show a native desktop notification. Returns True if plyer ran without raising."""
    try:
        from plyer import notification

        notification.notify(
            title=str(title)[:256],
            message=str(message)[:1024],
            app_name=app_name,
            timeout=10,
        )
        return True
    except Exception as exc:
        logger.debug("desktop notify failed: %s", exc)
        return False
