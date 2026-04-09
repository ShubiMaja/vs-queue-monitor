#!/usr/bin/env python3
# monitor.py
# Version: 1.0.0

import argparse
import os
import re
import sys
import time
from pathlib import Path

try:
    import winsound
except ImportError:
    winsound = None

QUEUE_RE = re.compile(r"Client is in connect queue at position:\s*(\d+)")
VERSION = "1.0.0"


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def normalize_path(raw: str) -> Path:
    if not raw:
        return Path()

    expanded = os.path.expandvars(raw)
    expanded = os.path.expanduser(expanded)

    # Normalize slashes
    expanded = expanded.replace("\\", "/")

    return Path(expanded)


def resolve_log_file(raw: str) -> Path | None:
    p = normalize_path(raw)

    if p.is_file():
        return p

    if p.is_dir():
        candidates = []

        # direct child
        direct = p / "client-main.log"
        if direct.is_file():
            return direct

        # recursive search
        for found in p.rglob("client-main.log"):
            candidates.append(found)

        if candidates:
            # pick the newest
            candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return candidates[0]

    return None


def read_latest_position(log_file: Path, tail_bytes: int = 65536) -> int | None:
    try:
        with log_file.open("rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            start = max(0, size - tail_bytes)
            f.seek(start)
            data = f.read().decode("utf-8", errors="ignore")
    except Exception:
        return None

    matches = QUEUE_RE.findall(data)
    if not matches:
        return None

    return int(matches[-1])


def play_alert(sound_repeats: int, sound_file: str | None) -> None:
    if winsound is None:
        return

    if sound_file:
        sf = resolve_log_file(sound_file) if Path(sound_file).is_dir() else normalize_path(sound_file)
        if sf and Path(sf).is_file():
            try:
                winsound.PlaySound(str(sf), winsound.SND_FILENAME)
                return
            except Exception:
                pass

    for _ in range(sound_repeats):
        try:
            winsound.Beep(1400, 250)
            time.sleep(0.1)
            winsound.Beep(1000, 250)
            time.sleep(0.1)
        except Exception:
            try:
                winsound.MessageBeep(winsound.MB_ICONHAND)
            except Exception:
                pass
            time.sleep(0.25)


def show_popup(title: str, message: str) -> None:
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x30)
    except Exception:
        pass


def should_alert(
    position: int,
    last_alert_position: int | None,
    last_alert_time: float,
    alert_at: int,
    position_step: int,
    repeat_alert_seconds: int,
) -> tuple[bool, str]:
    now = time.time()
    elapsed = now - last_alert_time

    if last_alert_position is None:
        if position <= alert_at:
            return True, f"position <= {alert_at}"
        return False, ""

    improvement = last_alert_position - position

    if position <= alert_at and elapsed >= repeat_alert_seconds:
        return True, f"still at or below {alert_at} after {int(elapsed)}s"

    if improvement >= position_step and elapsed >= repeat_alert_seconds:
        return True, f"improved by {improvement} since last alert"

    return False, ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor Vintage Story queue position and alert on Windows.")
    parser.add_argument("--file", "-f", default=r"%APPDATA%/VintagestoryData/client-main.log",
                        help="Path to client-main.log, or a directory to search")
    parser.add_argument("--alert-at", "-a", type=int, default=10,
                        help="Alert when queue position is <= this value")
    parser.add_argument("--step", "-s", type=int, default=5,
                        help="Alert when position improves by this many spots since last alert")
    parser.add_argument("--repeat-sec", "-r", type=int, default=30,
                        help="Minimum seconds between repeated alerts")
    parser.add_argument("--poll-sec", "-p", type=float, default=2.0,
                        help="Polling interval in seconds")
    parser.add_argument("--sound-repeats", type=int, default=8,
                        help="Number of beep repetitions")
    parser.add_argument("--sound-file", default="",
                        help="Optional WAV file to play instead of beeps")
    parser.add_argument("--show-every-change", action="store_true",
                        help="Print every queue change")
    parser.add_argument("--popup", type=int, choices=[0, 1], default=1,
                        help="Enable popup alerts")
    parser.add_argument("--sound", type=int, choices=[0, 1], default=1,
                        help="Enable sound alerts")

    args = parser.parse_args()

    log_file = resolve_log_file(args.file)

    log(f"monitor.py v{VERSION}")
    log(f"Input path: {args.file}")

    if not log_file:
        print("Log file not found.", file=sys.stderr)
        print("Try one of these:", file=sys.stderr)
        print(r'  python monitor.py --file "%APPDATA%\VintagestoryData\client-main.log"', file=sys.stderr)
        print(r'  python monitor.py --file "%APPDATA%\VSLInstallations\Unstable"', file=sys.stderr)
        print(r'  python monitor.py --file "%APPDATA%"', file=sys.stderr)
        return 1

    log(f"Watching: {log_file}")
    log(f"Alert when <= {args.alert_at}, step improvement {args.step}, repeat every {args.repeat_sec}s")

    last_position = None
    last_alert_position = None
    last_alert_time = 0.0

    try:
        while True:
            position = read_latest_position(log_file)

            if position is not None:
                if position != last_position:
                    if args.show_every_change or last_position is None:
                        log(f"Queue position: {position}")
                    last_position = position

                alert, reason = should_alert(
                    position=position,
                    last_alert_position=last_alert_position,
                    last_alert_time=last_alert_time,
                    alert_at=args.alert_at,
                    position_step=args.step,
                    repeat_alert_seconds=args.repeat_sec,
                )

                if alert:
                    log(f"ALERT: queue position {position} ({reason})")
                    last_alert_position = position
                    last_alert_time = time.time()

                    if args.sound:
                        play_alert(args.sound_repeats, args.sound_file or None)

                    if args.popup:
                        show_popup(
                            "Vintage Story Queue Alert",
                            f"Queue position is now {position}\n\nReason: {reason}"
                        )

            time.sleep(args.poll_sec)

    except KeyboardInterrupt:
        log("Stopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
