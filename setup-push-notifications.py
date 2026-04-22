"""Generate VAPID keys for mobile push notifications and write .env + .secrets/vapid_private.pem.

Run once:
    python setup-push-notifications.py

After running, restart VS Queue Monitor and then grant notification permission in the
browser (click the bell icon). Push notifications will work on any subscribed device.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
SECRETS_DIR = ROOT / ".secrets"
PRIVATE_KEY_FILE = SECRETS_DIR / "vapid_private.pem"


def _read_existing_env() -> dict[str, str]:
    if not ENV_FILE.is_file():
        return {}
    result: dict[str, str] = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip()
        if val and val[0] in ('"', "'") and val[-1] == val[0]:
            val = val[1:-1]
        result[key.strip()] = val
    return result


def _write_env(data: dict[str, str]) -> None:
    lines = []
    for key, val in data.items():
        lines.append(f"{key}={val}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    try:
        from py_vapid import Vapid
        import base64
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    except ImportError:
        print("ERROR: pywebpush is not installed. Run: pip install pywebpush")
        sys.exit(1)

    existing = _read_existing_env()

    # Check if already configured
    has_pub = bool(existing.get("VS_QUEUE_MONITOR_VAPID_PUBLIC_KEY", "").strip())
    has_priv = bool(existing.get("VS_QUEUE_MONITOR_VAPID_PRIVATE_KEY", "").strip())
    if has_pub and has_priv and PRIVATE_KEY_FILE.is_file():
        print("VAPID keys already configured in .env and .secrets/vapid_private.pem")
        print("No changes made. Delete .env and .secrets/vapid_private.pem to regenerate.")
        return

    # Ask for email (used as the VAPID subject)
    default_email = existing.get("VS_QUEUE_MONITOR_VAPID_SUBJECT", "").replace("mailto:", "").strip()
    prompt = f"Your email address (for VAPID subject) [{default_email or 'required'}]: "
    try:
        email = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(0)

    if not email:
        email = default_email
    if not email or "@" not in email:
        print("ERROR: a valid email address is required for the VAPID subject.")
        sys.exit(1)

    # Generate keys
    print("Generating VAPID keys...")
    v = Vapid()
    v.generate_keys()

    # Save private key
    SECRETS_DIR.mkdir(exist_ok=True)
    PRIVATE_KEY_FILE.write_bytes(v.private_pem())
    print(f"Private key saved to:  {PRIVATE_KEY_FILE.relative_to(ROOT)}")

    # Compute public key (URL-safe base64, no padding)
    pub_bytes = v.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    public_key = base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode()

    # Write .env (preserve unrelated keys)
    existing["VS_QUEUE_MONITOR_VAPID_SUBJECT"] = f"mailto:{email}"
    existing["VS_QUEUE_MONITOR_VAPID_PUBLIC_KEY"] = public_key
    existing["VS_QUEUE_MONITOR_VAPID_PRIVATE_KEY"] = str(PRIVATE_KEY_FILE.relative_to(ROOT)).replace("\\", "/")
    _write_env(existing)
    print(f".env written to:       {ENV_FILE.relative_to(ROOT)}")

    print()
    print("Done! Next steps:")
    print("  1. Restart VS Queue Monitor.")
    print("  2. Open the app in your browser (ideally over HTTPS — use ngrok or an SSH tunnel for mobile).")
    print("  3. Click the bell icon and grant notification permission.")
    print("  4. Push notifications will work on every subscribed device from then on.")
    print()
    print("Your public key (needed if you integrate other clients):")
    print(f"  {public_key}")


if __name__ == "__main__":
    main()
