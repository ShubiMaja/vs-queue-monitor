"""Windows embedded window: WebView2 notification permission.

Microsoft Edge WebView2 **blocks Web Notifications by default** until the host
handles ``PermissionRequested`` and sets **Allow** (unlike a normal browser tab).
pywebview does not wire this up, so ``Notification`` may exist but permission
never succeeds. We attach a handler after CoreWebView2 is ready.

We **poll quickly** for CoreWebView2 instead of a fixed long delay: if the user
clicks the bell and calls ``Notification.requestPermission()`` before our handler
exists, WebView2 can **deny** by default and desktop alerts never work for that
session.

See: WebView2Feedback #4488 (notifications blocked by default).
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_POLL_SEC = 0.05
_DEADLINE_SEC = 25.0


def schedule_webview2_notification_permission() -> None:
    """Background thread: attach PermissionRequested on the main WebView2 as soon as possible."""
    if sys.platform != "win32":
        return

    def worker() -> None:
        deadline = time.monotonic() + _DEADLINE_SEC
        attached = False
        kind_cls: Any = None
        state_cls: Any = None
        while time.monotonic() < deadline and not attached:
            try:
                import webview
            except Exception:
                return
            if not getattr(webview, "windows", None):
                time.sleep(_POLL_SEC)
                continue
            try:
                w = webview.windows[0]
            except (IndexError, AttributeError):
                time.sleep(_POLL_SEC)
                continue
            native = getattr(w, "native", None)
            if native is None:
                time.sleep(_POLL_SEC)
                continue
            ctrl = getattr(native, "webview", None)
            if ctrl is None:
                time.sleep(_POLL_SEC)
                continue
            try:
                core = ctrl.CoreWebView2
            except Exception:
                time.sleep(_POLL_SEC)
                continue
            if core is None:
                time.sleep(_POLL_SEC)
                continue

            if kind_cls is None:
                try:
                    import clr  # type: ignore[import-untyped]
                    from webview.util import interop_dll_path  # type: ignore[import-untyped]

                    clr.AddReference(interop_dll_path("Microsoft.Web.WebView2.Core.dll"))
                    from Microsoft.Web.WebView2.Core import (  # type: ignore[import-not-found]
                        CoreWebView2PermissionKind,
                        CoreWebView2PermissionState,
                    )

                    kind_cls = CoreWebView2PermissionKind
                    state_cls = CoreWebView2PermissionState
                except Exception as exc:
                    logger.debug("WebView2 notification patch: could not load Core types: %s", exc)
                    return

            def on_permission(sender: Any, args: Any, *, _k: Any = kind_cls, _s: Any = state_cls) -> None:
                try:
                    if args.PermissionKind == _k.Notifications:
                        args.State = _s.Allow
                except Exception:
                    try:
                        if "Notification" in str(args.PermissionKind):
                            args.State = _s.Allow
                    except Exception:
                        pass

            def attach() -> None:
                try:
                    core.PermissionRequested += on_permission
                    logger.debug("WebView2: PermissionRequested handler attached for notifications")
                except Exception as exc:
                    logger.debug("WebView2: could not attach PermissionRequested: %s", exc)

            try:
                from System import Action  # type: ignore[import-untyped]

                ctrl.Invoke(Action(attach))
                attached = True
            except Exception as exc:
                logger.debug("WebView2: Invoke for PermissionRequested failed: %s", exc)
                time.sleep(_POLL_SEC)

        if not attached:
            logger.debug("WebView2 notification patch: CoreWebView2 not ready within %.0fs", _DEADLINE_SEC)

    threading.Thread(target=worker, daemon=True, name="vsqm-webview2-notify").start()
