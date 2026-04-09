# Vintage Story Queue Monitor

Desktop app (Python + Tkinter) that tails the **Vintage Story** client log, tracks **connect queue position**, estimates **wait time**, and raises **alerts** when you cross configurable thresholds (popup + optional sound on Windows).

## Requirements

- **Python 3.10+** (tested on 3.14; any recent 3.x with Tkinter should work)
- **Tkinter** — usually bundled with Python on Windows; on Linux install your distro’s `python3-tk` package

No third-party pip dependencies.

## Run

```bash
python monitor.py
```

By default the app **starts monitoring** as soon as it opens (if the log path resolves). To open the UI without auto-start:

```bash
python monitor.py --no-start
```

Point at a **log file** or a **directory** to search (see below):

```bash
python monitor.py --path "%APPDATA%/VintagestoryData/client-main.log"
python monitor.py --path "C:\path\to\VintagestoryData"
```

## Log file

The game writes queue lines similar to:

- `Client is in connect queue at position: N`
- `Your position in the queue is: N`

Default path hint in the UI: `%APPDATA%/VintagestoryData/client-main.log` (Windows). If you pass a folder, the app looks for `client-main.log` (and a few fallbacks) under common layouts.

## Features (short)

| Area | Behavior |
|------|----------|
| **Status bar** | Position, status, elapsed, remaining ETA, progress (elapsed vs ETA when known) |
| **Graph** | Recent queue position over time; optional log-scaled Y axis |
| **Alerts** | Comma-separated thresholds (e.g. `10, 5, 3, 2, 1`); one shot per crossing per queue run |
| **Reconnect / interrupt** | Distinguishes grace-period TCP errors vs final teardown; optional log-silence detection; **Interrupted** freezes elapsed but **keeps tailing** the log |
| **New queue** | After an interrupt, if a **new queue run** appears in the log, a dialog offers to **re-seed** the graph for that run |
| **Config** | Settings and window geometry persist to JSON (see below) |

## Configuration file

Saved automatically (debounced) when you change options:

| OS | Path |
|----|------|
| Windows | `%APPDATA%\vs-q-monitor\config.json` |
| Linux/macOS | `$XDG_CONFIG_HOME/vs-q-monitor/config.json` or `~/.config/vs-q-monitor/config.json` |

Typical keys: `source_path`, `alert_thresholds`, `poll_sec`, `avg_window_points`, `show_log`, `graph_log_scale`, `popup_enabled`, `sound_enabled`, `show_every_change`, `window_geometry`.

## Development

```bash
python -m py_compile monitor.py
```

## License / game

This project is an independent tool for reading **your** client log. It is not affiliated with Vintage Story or its authors.
