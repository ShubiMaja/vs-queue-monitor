# VS Queue Monitor

**Python** app that tails the **Vintage Story** client log, tracks **connect queue position**, estimates **wait time**, and raises alerts at configurable thresholds. Three front ends share the same engine:

- **Local web UI** (default) — **`python monitor.py`** serves the UI on `http://127.0.0.1:8765/` (embedded window via **pywebview** when available; otherwise your browser). Inline KPI edits, canvas graph, PNG/TSV copy, spotlight tour (`starlette` + `uvicorn`; **pywebview** on Python 3.13 and older in `requirements.txt`).
- **Tk desktop GUI** (`--gui`) — classic window; graph, KPIs, sounds, OS notifications.
- **Textual terminal UI** (`--tui`) — SSH-friendly; no display required.

**Product and UX:** [`docs/DESIGN.md`](docs/DESIGN.md). **GUI vs TUI:** [`docs/GUI-TUI-PARITY.md`](docs/GUI-TUI-PARITY.md), [`docs/UI-UX-PARITY.md`](docs/UI-UX-PARITY.md), [`docs/TUI-LIMITATIONS.md`](docs/TUI-LIMITATIONS.md). **Architecture notes:** [`docs/real-life-ui-patterns.md`](docs/real-life-ui-patterns.md).

<img width="1916" height="1072" alt="VS Queue Monitor screenshot" src="https://github.com/user-attachments/assets/648649c3-264c-4880-9e80-7a46efc4d746" />

## Disclaimer (read this)

**No warranty — use at your own risk.** **Not affiliated with Vintage Story** or its developers. You must validate paths, alerts, ETAs, and time-sensitive decisions yourself.

- **Work in progress:** Features, UI, saved settings, and behavior can change at any time.
- **AI-assisted code:** Much of this codebase was produced or refactored with AI / coding assistants. Validate paths, alerts, ETAs, and log interpretation yourself.

## Requirements

- **Python 3.10+**
- **Starlette + uvicorn** — `pip install -r requirements.txt`; serves the **default** web UI on `127.0.0.1`.
- **pywebview** — pulled automatically on **Python 3.13 and older** for the embedded desktop shell. On **Python 3.14+**, `requirements.txt` skips it until wheels exist; use **`--web-browser`** or `pip install pywebview` when a build is available for your Python.
- **Tkinter** — for **`--gui`** only (classic window).
- **Textual** — same install; used for **`--tui`**.

## Quick start

```bash
pip install -r requirements.txt
python monitor.py
```

Same as `python -m vs_queue_monitor`. Default: web UI on `127.0.0.1`.

| | |
|--|--|
| Tk | `python monitor.py --gui` |
| TUI | `python monitor.py --tui` |
| Windows | `vsqm.cmd` / `Run VS Queue Monitor.bat` · `Win+R` → `vsqm` if the repo directory is on user **`Path`** · else `"…\vs-queue-monitor\vsqm.cmd"` |
| macOS / Linux | `./run-vs-queue-monitor.sh` or `python3 monitor.py` |

**Bootstrap** — default clone `~/vs-queue-monitor`; `VS_QUEUE_MONITOR_HOME` overrides. Forks: `VS_QUEUE_MONITOR_REPO`, `VS_QUEUE_MONITOR_BRANCH`. Non-`main` branch: fix the raw URL path (e.g. `feature%2Funified-approach`).

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

`python bootstrap.py` forwards the same flags as `monitor.py` (e.g. `--gui`, `--tui`, `--path "%APPDATA%\VintagestoryData"`).

Log path: folder above or containing `client-main.log` — [Pointing at the log](#pointing-at-the-log).

### Default web UI

`http://127.0.0.1:8765/` — webview when available; otherwise the default browser. **`--web-browser`** skips embedded. **`--web-port`** / **`VS_QUEUE_MONITOR_WEB_PORT`**. **Ctrl+C** stops the server. **`--web`** is a no-op alias for scripts.

Without a working `pywebview` install, stderr describes **`--web-browser`** or installing `pywebview`.

#### pip / `pythonnet` fails on Windows (Python 3.14+)

`pywebview` depends on **`pythonnet`** on Windows; building it from source can fail (e.g. NuGet / `pythonnet` wheel not available yet). **`pip install -r requirements.txt`** still succeeds because **`pywebview` is omitted on Python 3.14+** in `requirements.txt`. Use **`python monitor.py --web-browser`** for the full UI, or use a **Python 3.12** or **3.13** venv and run **`pip install pywebview`** if you need the embedded window.

#### Cross-platform (embedded window)

The default flow works on **Windows, macOS, and Linux** with a graphical session. [pywebview](https://pywebview.idepy.com/) uses the **native webview** on each OS (Edge **WebView2** on Windows, **WKWebView** on macOS, **WebKitGTK** on typical Linux desktops). The HTTP server always binds **`127.0.0.1`** only.

| OS | Typical prerequisites |
|----|------------------------|
| **Windows** | WebView2 runtime (usually present on Windows 10/11). |
| **macOS** | No extra system packages beyond `pip install -r requirements.txt`. |
| **Linux** | A desktop with **X11** or **Wayland** (`DISPLAY` / `WAYLAND_DISPLAY`). You may need distro packages for WebKitGTK (e.g. Debian/Ubuntu: `gir1.2-webkit2-4.1`, `gtk3`; names vary — see [pywebview prerequisites](https://pywebview.idepy.com/guide/installation.html)). |
| **Headless / SSH** | No embedded window; the app serves **`http://127.0.0.1:<port>/`** and prints how to use **`ssh -L`** or **`--web-browser`**. |

The web client supports **inline editing** (✎ on poll interval, rolling window, thresholds), **Copy graph as PNG**, **Copy graph (TSV)**, and a **guided spotlight tour** (runs once until completed; stored as `tutorial_done` in config, same key as the Tk welcome dialog).

### GUI (Tk, optional)

- **All platforms:** `python monitor.py --gui` for the classic Tk window.
- **VS Code / Cursor:** Run and Debug → **VS Queue Monitor: Run Tk GUI** (see [`.vscode/launch.json`](.vscode/launch.json)).

### TUI (Textual)

```bash
python monitor.py --tui
```

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
| `vs_queue_monitor/web/` | Local Starlette app + static client (default UI) |
| `vs_queue_monitor/cli.py` | Default web UI; `--gui` / `--tui` / `--web`, `--web-browser`, `--path`, `--no-start` |
| `monitor.py` | Entrypoint |
| `vsqm.cmd` | Windows: short launcher for **Win+R** / PATH; runs `monitor.py` (uses `.venv` if present) |
| `Run VS Queue Monitor.bat` | Windows: double-click; delegates to **`vsqm.cmd`** |
| `run-vs-queue-monitor.sh` | macOS/Linux: run from terminal (uses `.venv` if present) |
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
| *(none)* | **Default:** embedded web UI (pywebview on `127.0.0.1`) |
| `--web` | Same as default (explicit; for scripts) |
| `--web-browser` | Web UI in your default external browser instead of an embedded window |
| `--web-port PORT` | TCP port for the web UI (default `8765` or `VS_QUEUE_MONITOR_WEB_PORT`) |
| `--gui` | Tk window instead of the default web UI |
| `--tui` / `--text` | Textual TUI instead of the default web UI |
| `--path PATH` | Initial **Logs folder** (directory; resolves to `client-main.log` inside) |
| `--no-start` | Open without auto-starting monitoring |

## Install Python and Tkinter

### Windows

1. Install **Python** from [python.org](https://www.python.org/downloads/) (enable PATH; include **tcl/tk**).
2. In the project folder: `pip install -r requirements.txt` then `python monitor.py` (embedded web UI by default; use `--gui` for Tk).

### macOS

Install Python from [python.org](https://www.python.org/downloads/macos/) or Homebrew. If the window fails to open, use a Tk-enabled build (e.g. `brew install python-tk` where available).

### Linux (Debian / Ubuntu)

```bash
sudo apt update && sudo apt install python3 python3-tk
pip install -r requirements.txt
python3 monitor.py
```

(`python3 monitor.py` starts the **embedded web UI** by default; use `--gui` for Tk or `--tui` for the terminal UI.)

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
