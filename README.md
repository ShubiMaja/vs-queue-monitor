# VS Queue Monitor

**Python** app that tails the **Vintage Story** client log, tracks **connect queue position**, estimates **wait time**, and raises alerts at configurable thresholds. Three front ends share the same engine:

- **Tk desktop GUI** — graph, KPIs, sounds, OS notifications (default on Windows).
- **Textual terminal UI** (`--tui`) — SSH-friendly; no display required.
- **Local web UI** (`--web`) — **embedded desktop window** (pywebview) on `http://127.0.0.1:8765/` by default; use `--web-browser` for your default external browser. Inline KPI edits, canvas graph, PNG/TSV copy, spotlight tour (requires `starlette`, `uvicorn`, and `pywebview` from `requirements.txt`).

**Product and UX:** [`docs/DESIGN.md`](docs/DESIGN.md). **GUI vs TUI:** [`docs/GUI-TUI-PARITY.md`](docs/GUI-TUI-PARITY.md), [`docs/UI-UX-PARITY.md`](docs/UI-UX-PARITY.md), [`docs/TUI-LIMITATIONS.md`](docs/TUI-LIMITATIONS.md). **Architecture notes:** [`docs/real-life-ui-patterns.md`](docs/real-life-ui-patterns.md).

<img width="1916" height="1072" alt="VS Queue Monitor screenshot" src="https://github.com/user-attachments/assets/648649c3-264c-4880-9e80-7a46efc4d746" />

## Disclaimer (read this)

**No warranty — use at your own risk.** **Not affiliated with Vintage Story** or its developers. You must validate paths, alerts, ETAs, and time-sensitive decisions yourself.

- **Work in progress:** Features, UI, saved settings, and behavior can change at any time.
- **AI-assisted code:** Much of this codebase was produced or refactored with AI / coding assistants. Validate paths, alerts, ETAs, and log interpretation yourself.

## Requirements

- **Python 3.10+**
- **Tkinter** — for the GUI (`python monitor.py` / `--gui` on Windows by default).
- **Textual** — `pip install -r requirements.txt`; used for `--tui`.
- **Starlette + uvicorn + pywebview** — same install; used for `--web` (embedded window by default).

## Quick start

### One command from a single file (smooth setup)

Download **`bootstrap.py`** once (or pipe it), run it, and it will **git clone** the repo (if needed), create **`.venv`**, **pip install** dependencies, and start the app. Default clone location: **`~/vs-queue-monitor`** (override with env **`VS_QUEUE_MONITOR_HOME`**). Forks: set **`VS_QUEUE_MONITOR_REPO`** to your git URL; optional **`VS_QUEUE_MONITOR_BRANCH`**.

If **`bootstrap.py` is not on `main` yet**, replace `main` in the URL with your branch name (e.g. `feature/unified-approach` → path segment `feature%2Funified-approach`).

**macOS / Linux**

```bash
curl -fsSL https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap.py -o bootstrap.py && python3 bootstrap.py
```

**Pipe (no `bootstrap.py` on disk)**

```bash
curl -fsSL https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap.py | python3 -
```

**Windows (PowerShell)**

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap.py" -OutFile bootstrap.py
python bootstrap.py
```

Pass the same flags as usual, e.g. `python bootstrap.py --web`, `python bootstrap.py --tui`, `python bootstrap.py --path "%APPDATA%\VintagestoryData"`.

### Manual install (existing clone)

```bash
pip install -r requirements.txt
python monitor.py
```

Equivalent: `python -m vs_queue_monitor`. On Windows use `python` or `py` if needed.

### GUI (Tk)

- **Windows:** `python monitor.py` opens the window by default.
- **macOS / Linux:** `python3 monitor.py --gui` if you have a display.
- **VS Code / Cursor:** Run and Debug → **VS Queue Monitor: Run GUI (Python)** (see [`.vscode/launch.json`](.vscode/launch.json)).

### TUI (Textual)

```bash
python monitor.py --tui
```

On Linux/macOS without `DISPLAY`, the app may pick the TUI automatically unless you set `VS_QUEUE_MONITOR_UI=gui` or pass `--gui`.

### Web (embedded window)

```bash
pip install -r requirements.txt
python monitor.py --web
```

Opens the UI in a **desktop window** (pywebview / system webview) pointed at `http://127.0.0.1:8765/` — not a separate browser app. Use **`--web-browser`** if you prefer the old behavior (default OS browser). Use `--web-port 9000` or env `VS_QUEUE_MONITOR_WEB_PORT` to change the port. Closing the window stops the app; **Ctrl+C** in the terminal also stops the server.

If `pywebview` is not installed (or `pip install` failed on a very new Python version), the server still runs and stderr explains how to install it or use **`--web-browser`**.

#### `--web` cross-platform (embedded window)

The same **`python monitor.py --web`** flow works on **Windows, macOS, and Linux** with a graphical session. [pywebview](https://pywebview.idepy.com/) uses the **native webview** on each OS (Edge **WebView2** on Windows, **WKWebView** on macOS, **WebKitGTK** on typical Linux desktops). The HTTP server always binds **`127.0.0.1`** only.

| OS | Typical prerequisites |
|----|------------------------|
| **Windows** | WebView2 runtime (usually present on Windows 10/11). |
| **macOS** | No extra system packages beyond `pip install -r requirements.txt`. |
| **Linux** | A desktop with **X11** or **Wayland** (`DISPLAY` / `WAYLAND_DISPLAY`). You may need distro packages for WebKitGTK (e.g. Debian/Ubuntu: `gir1.2-webkit2-4.1`, `gtk3`; names vary — see [pywebview prerequisites](https://pywebview.idepy.com/guide/installation.html)). |
| **Headless / SSH** | No embedded window; the app serves **`http://127.0.0.1:<port>/`** and prints how to use **`ssh -L`** or **`--web-browser`**. |

The web client supports **inline editing** (✎ on poll interval, rolling window, thresholds), **Copy graph as PNG**, **Copy graph (TSV)**, and a **guided spotlight tour** (runs once until completed; stored as `tutorial_done` in config, same key as the Tk welcome dialog).

**TUI shortcuts:** **Space** start/stop, **o** settings, **F1** help, **c** copy graph (TSV), **v** copy session log, **q** quit — full list in [`docs/GUI-TUI-PARITY.md`](docs/GUI-TUI-PARITY.md). Legacy: `python monitor-tui.py` = `python monitor.py --tui`.

**GUI:** **F1** opens Help (paths and config location). **Copy History** / **Copy graph (TSV)** copy to the clipboard. **Live view** (on the chart and under Settings → Graph) keeps the time axis aligned with the current time while monitoring. A short welcome dialog runs once until dismissed (stored as `tutorial_done` in config).

### Without auto-start

```bash
python monitor.py --no-start
```

## Project layout

| Path | Role |
|------|------|
| `vs_queue_monitor/core.py` | Parsing, config, log I/O — no UI |
| `vs_queue_monitor/engine.py` | Shared monitor logic |
| `vs_queue_monitor/gui.py` | Tk UI |
| `vs_queue_monitor/tui.py` | Textual UI |
| `vs_queue_monitor/web/` | Local Starlette app + static browser client (`--web`) |
| `vs_queue_monitor/cli.py` | `--gui` / `--tui` / `--web`, `--web-browser`, `--path`, `--no-start` |
| `monitor.py` | Entrypoint |
| `bootstrap.py` | One-file launcher: clone (if needed), venv, `pip install`, run `monitor.py` |
| `tools/build_engine.py` | Regenerates `engine.py` from `_engine_raw.py` when using that workflow |
| `_engine_raw.py` | Input for `tools/build_engine.py` |

## Pointing at the log

Pass a **folder** (Vintage Story **data** directory, or a folder that contains the client log). The app resolves **`client-main.log`** (and fallbacks) — you do not enter a `.log` file in the main path field.

**Windows**

```powershell
python monitor.py --path "%APPDATA%\VintagestoryData"
```

**macOS / Linux**

```bash
python3 monitor.py --path "$HOME/Library/Application Support/VintagestoryData"
python3 monitor.py --path "$HOME/.config/VintagestoryData"
```

If no log exists yet, status stays **Waiting for log file** until the game creates one.

## Command-line interface

| Argument | Meaning |
|----------|---------|
| `--gui` | Force Tk window |
| `--tui` / `--text` | Force Textual TUI |
| `--path PATH` | Initial **Logs folder** (directory; resolves to `client-main.log` inside) |
| `--no-start` | Open without auto-starting monitoring |

## Install Python and Tkinter

### Windows

1. Install **Python** from [python.org](https://www.python.org/downloads/) (enable PATH; include **tcl/tk**).
2. In the project folder: `pip install -r requirements.txt` then `python monitor.py`.

### macOS

Install Python from [python.org](https://www.python.org/downloads/macos/) or Homebrew. If the window fails to open, use a Tk-enabled build (e.g. `brew install python-tk` where available).

### Linux (Debian / Ubuntu)

```bash
sudo apt update && sudo apt install python3 python3-tk
pip install -r requirements.txt
python3 monitor.py
```

## Log file (game output)

The client log lines look like:

- `Client is in connect queue at position: N`
- `Your position in the queue is: N`

## Behavior (summary)

Detailed intent is in [`docs/DESIGN.md`](docs/DESIGN.md). This section is a short operational summary.

### Dashboard

- **KPIs:** Position (including **0** when past connect-queue wait per tail rules), status, rolling rate, warning thresholds, elapsed, ETA, progress.
- **Graph:** Step chart of queue position vs time for the **current queue session**; log/linear Y where available.
- **Info / History:** Collapsible in GUI; optional per-step queue lines when **Log every position change** is on (default **on**).

### Queue semantics

- **Completed** requires **post-queue** lines after the last queue position line in the tail — not merely reaching position `1`.
- **Interrupted** freezes rate/elapsed display appropriately while still polling when useful.

### Alerts

- **Thresholds:** comma-separated positions (default `10, 5, 1`); fire on **downward** crossings, once per threshold per run.
- **Completion:** when the tail shows past-queue activity after the last queue line.
- **Sounds / popups / OS notifications:** configurable per channel in Settings.

### Settings

- Stored in **`config.json`** (see `vs_queue_monitor.core.get_config_path()`). Same settings for GUI and TUI where applicable.

### Without Git (source archive)

Download the repo as ZIP or tarball from GitHub, extract, then `pip install -r requirements.txt` and `python monitor.py` as above.

## License / game

Independent tool for reading **your** client log. Not affiliated with Vintage Story or its authors.
