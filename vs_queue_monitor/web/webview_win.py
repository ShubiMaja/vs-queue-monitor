"""Windows embedded window: WebView2 notification permission.

Microsoft Edge WebView2 **blocks Web Notifications by default** until the host
handles ``PermissionRequested`` and sets **Allow** (unlike a normal browser tab).
pywebview does not wire this up, so ``Notification`` may exist but permission
never succeeds. We attach a handler after CoreWebView2 is ready.

See: WebView2Feedback #4488 (notifications blocked by default).
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


def schedule_webview2_notification_permission() -> None:
    """Start a background thread that attaches PermissionRequested on the main WebView2."""
    if sys.platform != "win32":
        return

    def worker() -> None:
        time.sleep(2.0)
        try:
            import webview
        except Exception:
            return
        if not getattr(webview, "windows", None):
            return
        try:
            w = webview.windows[0]
        except (IndexError, AttributeError):
            return
        native = getattr(w, "native", None)
        if native is None:
            return
        ctrl = getattr(native, "webview", None)
        if ctrl is None:
            return
        try:
            core = ctrl.CoreWebView2
        except Exception:
            return
        if core is None:
            return

        try:
            try:
                import clr  # type: ignore[import-untyped]
            except Exception:
                return
            from webview.util import interop_dll_path  # type: ignore[import-untyped]

            clr.AddReference(interop_dll_path("Microsoft.Web.WebView2.Core.dll"))
            from Microsoft.Web.WebView2.Core import (  # type: ignore[import-not-found]
                CoreWebView2PermissionKind,
                CoreWebView2PermissionState,
            )
        except Exception as exc:
            logger.debug("WebView2 notification patch: could not load Core types: %s", exc)
            return

        def on_permission(sender: Any, args: Any) -> None:
            try:
                if args.PermissionKind == CoreWebView2PermissionKind.Notifications:
                    args.State = CoreWebView2PermissionState.Allow
            except Exception:
                try:
                    if "Notification" in str(args.PermissionKind):
                        args.State = CoreWebView2PermissionState.Allow
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
        except Exception as exc:
            logger.debug("WebView2: Invoke for PermissionRequested failed: %s", exc)

    threading.Thread(target=worker, daemon=True, name="vsqm-webview2-notify").start()
