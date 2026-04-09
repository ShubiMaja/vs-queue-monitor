#!/usr/bin/env python3
"""
Vintage Story Queue Monitor GUI
Version: 1.0.0

Cross-platform Tkinter app that watches a Vintage Story client log for queue
position changes and raises popup + sound alerts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import traceback
from collections import deque
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import winsound  # type: ignore
except Exception:  # pragma: no cover
    winsound = None

VERSION = "1.0.0"
QUEUE_RE = re.compile(r"Client is in connect queue at position:\s*(\d+)")
DEFAULT_PATH = "$APPDATA/VintagestoryData/client-main.log"
TAIL_BYTES = 128 * 1024
POPUP_TIMEOUT_MS = 12_000
MAX_GRAPH_POINTS = 360


def expand_path(raw: str) -> Path:
    expanded = os.path.expandvars(raw.strip())
    expanded = os.path.expanduser(expanded)
    return Path(expanded)


def get_config_path() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
        return base / "vs-q-monitor" / "config.json"
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "vs-q-monitor" / "config.json"


def load_config() -> dict:
    path = get_config_path()
    try:
        if not path.is_file():
            return {}
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def save_config(data: dict) -> None:
    path = get_config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
        tmp.replace(path)
    except Exception:
        pass


def resolve_log_file(raw: str) -> Optional[Path]:
    path = expand_path(raw)

    if path.is_file():
        return path

    if not path.exists() or not path.is_dir():
        return None

    candidate_paths: list[Path] = [
        path / "client-main.log",
        path / "Logs" / "client-main.log",
        path / "logs" / "client-main.log",
        path / "client.log",
        path / "Logs" / "client.log",
        path / "logs" / "client.log",
    ]

    for candidate in candidate_paths:
        if candidate.is_file():
            return candidate

    matches: list[Path] = []
    patterns = ["client-main.log", "*client-main*.log", "*client*.log"]
    for pattern in patterns:
        try:
            matches.extend(path.rglob(pattern))
        except Exception:
            pass

    file_matches = [m for m in matches if m.is_file()]
    if not file_matches:
        return None

    file_matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return file_matches[0]


def read_latest_position(log_file: Path) -> Optional[int]:
    try:
        with log_file.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            start = max(0, size - TAIL_BYTES)
            handle.seek(start)
            data = handle.read().decode("utf-8", errors="ignore")
    except Exception:
        return None

    matches = QUEUE_RE.findall(data)
    if not matches:
        return None
    return int(matches[-1])


class QueueMonitorApp(tk.Tk):
    def __init__(self, initial_path: str = "", auto_start: bool = False) -> None:
        super().__init__()
        self.title(f"Vintage Story Queue Monitor v{VERSION}")
        self.geometry("930x640")
        self.minsize(860, 560)

        self.config: dict = load_config()
        self.source_path_var = tk.StringVar(
            value=initial_path or self.config.get("source_path", "") or DEFAULT_PATH,
        )
        self.resolved_path_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Idle")
        self.position_var = tk.StringVar(value="—")
        self.last_change_var = tk.StringVar(value="—")
        self.last_alert_var = tk.StringVar(value="—")
        self.alert_at_var = tk.StringVar(value=str(self.config.get("alert_at", "10")))
        self.step_var = tk.StringVar(value=str(self.config.get("step", "5")))
        self.repeat_sec_var = tk.StringVar(value=str(self.config.get("repeat_sec", "30")))
        self.poll_sec_var = tk.StringVar(value=str(self.config.get("poll_sec", "2")))
        self.popup_enabled_var = tk.BooleanVar(value=bool(self.config.get("popup_enabled", True)))
        self.sound_enabled_var = tk.BooleanVar(value=bool(self.config.get("sound_enabled", True)))
        self.show_every_change_var = tk.BooleanVar(value=bool(self.config.get("show_every_change", False)))

        self.running = False
        self.job_id: Optional[str] = None
        self.current_log_file: Optional[Path] = None
        self.last_position: Optional[int] = None
        self.last_alert_position: Optional[int] = None
        self.last_alert_epoch: float = 0.0
        self.active_popup: Optional[tk.Toplevel] = None
        self.graph_points: deque[tuple[float, int]] = deque(maxlen=MAX_GRAPH_POINTS)
        self.graph_canvas: Optional[tk.Canvas] = None

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.write_history(f"App started. Waiting for a path. Parser looks for queue lines like 'Client is in connect queue at position: N'.")

        try:
            geometry = self.config.get("window_geometry", "")
            if isinstance(geometry, str) and geometry:
                self.geometry(geometry)
        except Exception:
            pass

        if auto_start:
            self.after(250, self.start_monitoring)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        controls = ttk.LabelFrame(outer, text="Monitor")
        controls.pack(fill="x")
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="File or directory").grid(row=0, column=0, sticky="w", padx=8, pady=8)
        entry = ttk.Entry(controls, textvariable=self.source_path_var)
        entry.grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        ttk.Button(controls, text="Browse File", command=self.browse_file).grid(row=0, column=2, padx=4, pady=8)
        ttk.Button(controls, text="Browse Folder", command=self.browse_folder).grid(row=0, column=3, padx=4, pady=8)

        settings = ttk.Frame(controls)
        settings.grid(row=1, column=0, columnspan=4, sticky="ew", padx=8, pady=(0, 8))
        for idx in range(10):
            settings.columnconfigure(idx, weight=0)
        settings.columnconfigure(9, weight=1)

        ttk.Label(settings, text="Alert at ≤").grid(row=0, column=0, sticky="w", padx=(0, 4))
        ttk.Entry(settings, width=6, textvariable=self.alert_at_var).grid(row=0, column=1, padx=(0, 12))
        ttk.Label(settings, text="Step").grid(row=0, column=2, sticky="w", padx=(0, 4))
        ttk.Entry(settings, width=6, textvariable=self.step_var).grid(row=0, column=3, padx=(0, 12))
        ttk.Label(settings, text="Repeat sec").grid(row=0, column=4, sticky="w", padx=(0, 4))
        ttk.Entry(settings, width=6, textvariable=self.repeat_sec_var).grid(row=0, column=5, padx=(0, 12))
        ttk.Label(settings, text="Poll sec").grid(row=0, column=6, sticky="w", padx=(0, 4))
        ttk.Entry(settings, width=6, textvariable=self.poll_sec_var).grid(row=0, column=7, padx=(0, 12))

        ttk.Checkbutton(settings, text="Popup", variable=self.popup_enabled_var).grid(row=0, column=8, padx=(0, 8))
        ttk.Checkbutton(settings, text="Sound", variable=self.sound_enabled_var).grid(row=0, column=9, padx=(0, 8), sticky="w")
        ttk.Checkbutton(settings, text="Show every change", variable=self.show_every_change_var).grid(row=0, column=10, padx=(0, 8), sticky="w")

        buttons = ttk.Frame(controls)
        buttons.grid(row=2, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 10))
        ttk.Button(buttons, text="Start", command=self.start_monitoring).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Stop", command=self.stop_monitoring).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Resolve Path", command=self.resolve_and_show).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Reset defaults", command=self.reset_defaults).pack(side="left", padx=(0, 8))

        graph_frame = ttk.LabelFrame(outer, text="Queue graph")
        graph_frame.pack(fill="x", pady=(12, 0))
        graph_frame.columnconfigure(0, weight=1)
        self.graph_canvas = tk.Canvas(graph_frame, height=170, highlightthickness=0, background="white")
        self.graph_canvas.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        self.graph_canvas.bind("<Configure>", lambda _evt: self.redraw_graph())

        status = ttk.LabelFrame(outer, text="Status")
        status.pack(fill="x", pady=(12, 0))
        status.columnconfigure(1, weight=1)

        rows = [
            ("Status", self.status_var),
            ("Current queue position", self.position_var),
            ("Last change", self.last_change_var),
            ("Last alert", self.last_alert_var),
            ("Resolved log path", self.resolved_path_var),
        ]
        for row_idx, (label_text, var) in enumerate(rows):
            ttk.Label(status, text=label_text).grid(row=row_idx, column=0, sticky="nw", padx=8, pady=6)
            ttk.Label(status, textvariable=var, wraplength=720).grid(row=row_idx, column=1, sticky="nw", padx=8, pady=6)

        history_frame = ttk.LabelFrame(outer, text="History")
        history_frame.pack(fill="both", expand=True, pady=(12, 0))
        history_frame.rowconfigure(0, weight=1)
        history_frame.columnconfigure(0, weight=1)

        self.history_text = tk.Text(history_frame, height=20, wrap="word", state="disabled")
        self.history_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.history_text.configure(yscrollcommand=scrollbar.set)

    def get_config_snapshot(self) -> dict:
        return {
            "source_path": self.source_path_var.get(),
            "alert_at": self.alert_at_var.get(),
            "step": self.step_var.get(),
            "repeat_sec": self.repeat_sec_var.get(),
            "poll_sec": self.poll_sec_var.get(),
            "popup_enabled": bool(self.popup_enabled_var.get()),
            "sound_enabled": bool(self.sound_enabled_var.get()),
            "show_every_change": bool(self.show_every_change_var.get()),
            "window_geometry": self.geometry(),
            "version": VERSION,
        }

    def persist_config(self) -> None:
        save_config(self.get_config_snapshot())

    def reset_defaults(self) -> None:
        self.stop_monitoring()

        self.source_path_var.set(DEFAULT_PATH)
        self.alert_at_var.set("10")
        self.step_var.set("5")
        self.repeat_sec_var.set("30")
        self.poll_sec_var.set("2")
        self.popup_enabled_var.set(True)
        self.sound_enabled_var.set(True)
        self.show_every_change_var.set(False)

        self.resolved_path_var.set("")
        self.status_var.set("Idle")
        self.position_var.set("—")
        self.last_change_var.set("—")
        self.last_alert_var.set("—")

        self.graph_points.clear()
        self.redraw_graph()

        self.persist_config()
        self.write_history("Settings reset to defaults.")

    def write_history(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.history_text.configure(state="normal")
        self.history_text.insert("end", f"[{timestamp}] {message}\n")
        self.history_text.see("end")
        self.history_text.configure(state="disabled")

    def browse_file(self) -> None:
        selected = filedialog.askopenfilename(title="Select client log")
        if selected:
            self.source_path_var.set(selected)

    def browse_folder(self) -> None:
        selected = filedialog.askdirectory(title="Select folder to search")
        if selected:
            self.source_path_var.set(selected)

    def resolve_and_show(self) -> None:
        resolved = resolve_log_file(self.source_path_var.get())
        if resolved:
            self.resolved_path_var.set(str(resolved))
            self.write_history(f"Resolved path to: {resolved}")
            messagebox.showinfo("Resolved", f"Using log file:\n\n{resolved}")
        else:
            self.resolved_path_var.set("")
            messagebox.showerror("Not found", "Could not find client-main.log from that file or directory.")

    def parse_int(self, raw: str, name: str, minimum: int = 0) -> int:
        try:
            value = int(float(raw))
        except Exception as exc:
            raise ValueError(f"{name} must be a number") from exc
        if value < minimum:
            raise ValueError(f"{name} must be >= {minimum}")
        return value

    def parse_float(self, raw: str, name: str, minimum: float = 0.1) -> float:
        try:
            value = float(raw)
        except Exception as exc:
            raise ValueError(f"{name} must be a number") from exc
        if value < minimum:
            raise ValueError(f"{name} must be >= {minimum}")
        return value

    def start_monitoring(self) -> None:
        try:
            resolved = resolve_log_file(self.source_path_var.get())
            if not resolved:
                raise ValueError("Could not find client-main.log from that file or directory.")

            self.alert_at = self.parse_int(self.alert_at_var.get(), "Alert at", 1)
            self.step = self.parse_int(self.step_var.get(), "Step", 1)
            self.repeat_sec = self.parse_int(self.repeat_sec_var.get(), "Repeat sec", 1)
            self.poll_sec = self.parse_float(self.poll_sec_var.get(), "Poll sec", 0.2)

            self.current_log_file = resolved
            self.resolved_path_var.set(str(resolved))
            self.running = True
            self.status_var.set("Monitoring")
            self.write_history(f"Monitoring started. Log file: {resolved}")
            self.persist_config()

            if self.job_id is not None:
                self.after_cancel(self.job_id)
                self.job_id = None

            self.poll_once()
        except Exception as exc:
            self.status_var.set("Error")
            messagebox.showerror("Start failed", str(exc))

    def stop_monitoring(self) -> None:
        self.running = False
        self.status_var.set("Stopped")
        if self.job_id is not None:
            self.after_cancel(self.job_id)
            self.job_id = None
        self.write_history("Monitoring stopped.")

    def poll_once(self) -> None:
        if not self.running:
            return

        try:
            resolved = resolve_log_file(self.source_path_var.get())
            if resolved is not None:
                if self.current_log_file != resolved:
                    self.current_log_file = resolved
                    self.resolved_path_var.set(str(resolved))
                    self.write_history(f"Now watching: {resolved}")

            if not self.current_log_file or not self.current_log_file.is_file():
                self.status_var.set("Waiting for log file")
            else:
                position = read_latest_position(self.current_log_file)
                if position is not None:
                    self.status_var.set("Monitoring")
                    self.position_var.set(str(position))
                    self.append_graph_point(position)

                    if position != self.last_position:
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        self.last_change_var.set(timestamp)
                        if self.show_every_change_var.get() or self.last_position is None:
                            self.write_history(f"Queue position: {position}")
                        else:
                            self.write_history(f"Queue changed: {self.last_position} → {position}")
                        self.last_position = position

                    should_alert, reason = self.compute_alert(position)
                    if should_alert:
                        self.raise_alert(position, reason)
                else:
                    self.status_var.set("Watching log, queue line not found yet")
        except Exception as exc:
            self.status_var.set("Error")
            self.write_history(f"Error: {exc}")
            self.write_history(traceback.format_exc().splitlines()[-1])

        self.job_id = self.after(int(self.poll_sec * 1000), self.poll_once)

    def append_graph_point(self, position: int) -> None:
        now = time.time()
        self.graph_points.append((now, position))
        self.redraw_graph()

    def redraw_graph(self) -> None:
        canvas = self.graph_canvas
        if canvas is None:
            return
        canvas.delete("all")

        width = int(canvas.winfo_width())
        height = int(canvas.winfo_height())
        if width <= 10 or height <= 10:
            return

        pad_x = 12
        pad_y = 10
        plot_w = max(1, width - 2 * pad_x)
        plot_h = max(1, height - 2 * pad_y)

        points = list(self.graph_points)
        if len(points) < 2:
            canvas.create_rectangle(pad_x, pad_y, pad_x + plot_w, pad_y + plot_h, outline="#d0d0d0")
            if len(points) == 1:
                _t, pos = points[0]
                canvas.create_text(pad_x + 6, pad_y + 6, anchor="nw", text=f"{pos}", fill="#555555")
            else:
                canvas.create_text(pad_x + 6, pad_y + 6, anchor="nw", text="No data yet", fill="#777777")
            return

        t0 = points[0][0]
        t1 = points[-1][0]
        if t1 <= t0:
            t1 = t0 + 1e-6

        vals = [p for _t, p in points]
        vmin = min(vals)
        vmax = max(vals)
        if vmax == vmin:
            vmax = vmin + 1

        def x_of(t: float) -> float:
            return pad_x + (t - t0) / (t1 - t0) * plot_w

        def y_of(v: int) -> float:
            return pad_y + (v - vmin) / (vmax - vmin) * plot_h

        canvas.create_rectangle(pad_x, pad_y, pad_x + plot_w, pad_y + plot_h, outline="#d0d0d0")
        canvas.create_text(pad_x + 6, pad_y + 6, anchor="nw", text=f"min {vmin}  max {vmax}", fill="#555555")

        line = []
        for t, v in points:
            line.extend([x_of(t), y_of(v)])
        canvas.create_line(*line, fill="#2b7cff", width=2, smooth=False)

        last_t, last_v = points[-1]
        lx = x_of(last_t)
        ly = y_of(last_v)
        canvas.create_oval(lx - 3, ly - 3, lx + 3, ly + 3, outline="#2b7cff", fill="#2b7cff")
        canvas.create_text(lx + 8, ly, anchor="w", text=str(last_v), fill="#2b7cff")

    def compute_alert(self, position: int) -> tuple[bool, str]:
        now = time.time()
        elapsed = now - self.last_alert_epoch

        if self.last_alert_position is None:
            if position <= self.alert_at:
                return True, f"position <= {self.alert_at}"
            return False, ""

        improvement = self.last_alert_position - position
        if position <= self.alert_at and elapsed >= self.repeat_sec:
            return True, f"still at or below {self.alert_at} after {int(elapsed)}s"

        if improvement >= self.step and elapsed >= self.repeat_sec:
            return True, f"improved by {improvement} since last alert"

        return False, ""

    def raise_alert(self, position: int, reason: str) -> None:
        self.last_alert_position = position
        self.last_alert_epoch = time.time()
        self.last_alert_var.set(time.strftime("%Y-%m-%d %H:%M:%S"))
        self.write_history(f"ALERT: queue position {position} ({reason})")

        if self.sound_enabled_var.get():
            self.play_sound()
        if self.popup_enabled_var.get():
            self.show_popup(position, reason)

    def play_sound(self) -> None:
        if winsound is not None and sys.platform.startswith("win"):
            for _ in range(6):
                try:
                    winsound.Beep(1400, 180)
                    winsound.Beep(1000, 180)
                except Exception:
                    break
        else:
            self._ring_bell(0)

    def _ring_bell(self, count: int) -> None:
        if count >= 6:
            return
        try:
            self.bell()
        except Exception:
            pass
        self.after(220, lambda: self._ring_bell(count + 1))

    def show_popup(self, position: int, reason: str) -> None:
        if self.active_popup is not None and self.active_popup.winfo_exists():
            try:
                self.active_popup.destroy()
            except Exception:
                pass

        popup = tk.Toplevel(self)
        self.active_popup = popup
        popup.title("Queue Alert")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)
        popup.configure(padx=18, pady=18)

        try:
            popup.transient(self)
        except Exception:
            pass

        ttk.Label(
            popup,
            text=f"Queue position is now {position}",
            font=("TkDefaultFont", 15, "bold"),
        ).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            popup,
            text=f"Reason: {reason}",
            wraplength=360,
        ).pack(anchor="w", pady=(0, 12))
        ttk.Button(popup, text="Dismiss", command=popup.destroy).pack(anchor="e")

        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        x = max(40, screen_w - width - 50)
        y = max(40, screen_h - height - 90)
        popup.geometry(f"+{x}+{y}")

        popup.after(POPUP_TIMEOUT_MS, lambda: popup.winfo_exists() and popup.destroy())

    def on_close(self) -> None:
        self.persist_config()
        self.stop_monitoring()
        self.destroy()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vintage Story Queue Monitor GUI")
    parser.add_argument("--path", dest="path", default="", help="Initial file or directory path")
    parser.add_argument("--start", action="store_true", help="Auto-start monitoring after launch")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    app = QueueMonitorApp(initial_path=args.path, auto_start=args.start)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
