"""Web Push subscription storage and send helpers for the web UI."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from ..core import get_config_path


def _load_dotenv() -> None:
    """Load key=value pairs from a .env file next to the project root into os.environ.

    Only sets variables that are not already set in the environment. Supports
    bare values and quoted values (single or double). Lines starting with # are
    ignored. The .env file is looked for relative to this file's package tree.
    """
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.is_file():
        return
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if val and val[0] in ('"', "'") and val[-1] == val[0]:
                val = val[1:-1]
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception:
        pass


_load_dotenv()

try:
    from pywebpush import WebPushException, webpush  # type: ignore
except Exception:  # pragma: no cover
    WebPushException = Exception  # type: ignore
    webpush = None  # type: ignore

_PUSH_LOCK = threading.RLock()


def _env_pref(primary: str, *legacy: str) -> str:
    value = (os.environ.get(primary, "") or "").strip()
    if value:
        return value
    for name in legacy:
        value = (os.environ.get(name, "") or "").strip()
        if value:
            return value
    return ""


def push_store_path() -> Path:
    cfg = get_config_path()
    return cfg.with_name("push_subscriptions.json")


def vapid_public_key() -> str:
    return _env_pref("VS_QUEUE_MONITOR_VAPID_PUBLIC_KEY", "VSQM_VAPID_PUBLIC_KEY")


def vapid_private_key() -> str:
    raw = _env_pref("VS_QUEUE_MONITOR_VAPID_PRIVATE_KEY", "VSQM_VAPID_PRIVATE_KEY")
    if not raw:
        return ""
    # If it looks like a file path (ends with .pem or .key or contains a separator),
    # resolve it relative to the project root (.env file location).
    p = Path(raw)
    if not p.is_absolute() and (raw.endswith(".pem") or raw.endswith(".key") or "/" in raw or "\\" in raw):
        project_root = Path(__file__).resolve().parent.parent.parent
        abs_p = (project_root / p).resolve()
        if abs_p.is_file():
            return str(abs_p)
    return raw


def vapid_subject() -> str:
    return _env_pref(
        "VS_QUEUE_MONITOR_VAPID_SUBJECT",
        "VSQM_VAPID_SUBJECT",
        "WEBPUSH_VAPID_SUBJECT",
    ) or "mailto:vsqm@example.invalid"


def push_configured() -> bool:
    return bool(webpush and vapid_public_key() and vapid_private_key())


def push_status() -> dict[str, Any]:
    return {
        "configured": push_configured(),
        "pywebpush_available": bool(webpush),
        "has_public_key": bool(vapid_public_key()),
        "has_private_key": bool(vapid_private_key()),
        "subject": vapid_subject(),
        "store_path": str(push_store_path()),
    }


def _load_subscriptions() -> list[dict[str, Any]]:
    path = push_store_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("endpoint"), str) and item.get("endpoint", "").strip():
            out.append(item)
    return out


def _save_subscriptions(items: list[dict[str, Any]]) -> None:
    path = push_store_path()
    path.write_text(json.dumps(items, indent=2, sort_keys=True), encoding="utf-8")


def register_subscription(subscription: dict[str, Any], *, user_agent: str = "") -> dict[str, Any]:
    endpoint = str(subscription.get("endpoint", "") or "").strip()
    keys = subscription.get("keys")
    if not endpoint or not isinstance(keys, dict):
        raise ValueError("invalid push subscription")
    normalized = {
        "endpoint": endpoint,
        "keys": {
            "p256dh": str(keys.get("p256dh", "") or "").strip(),
            "auth": str(keys.get("auth", "") or "").strip(),
        },
        "user_agent": user_agent.strip(),
    }
    if not normalized["keys"]["p256dh"] or not normalized["keys"]["auth"]:
        raise ValueError("invalid push subscription keys")
    with _PUSH_LOCK:
        items = _load_subscriptions()
        items = [item for item in items if item.get("endpoint") != endpoint]
        items.append(normalized)
        _save_subscriptions(items)
        return {"stored": True, "count": len(items), "endpoint": endpoint}


def remove_subscription(endpoint: str) -> bool:
    endpoint = (endpoint or "").strip()
    if not endpoint:
        return False
    with _PUSH_LOCK:
        items = _load_subscriptions()
        kept = [item for item in items if item.get("endpoint") != endpoint]
        if len(kept) == len(items):
            return False
        _save_subscriptions(kept)
        return True


def subscription_count() -> int:
    with _PUSH_LOCK:
        return len(_load_subscriptions())


def send_push_to_all(payload: dict[str, Any]) -> dict[str, Any]:
    if not push_configured():
        raise RuntimeError("web push is not configured")
    assert webpush is not None
    body = json.dumps(payload)
    sent = 0
    removed = 0
    with _PUSH_LOCK:
        items = _load_subscriptions()
        kept: list[dict[str, Any]] = []
        for item in items:
            try:
                webpush(
                    subscription_info=item,
                    data=body,
                    vapid_private_key=vapid_private_key(),
                    vapid_claims={"sub": vapid_subject()},
                )
                kept.append(item)
                sent += 1
            except WebPushException as exc:  # type: ignore[misc]
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                if status_code in (404, 410):
                    removed += 1
                    continue
                kept.append(item)
            except Exception:
                kept.append(item)
        if kept != items:
            _save_subscriptions(kept)
    return {"sent": sent, "removed": removed, "remaining": len(kept)}
