# VS Queue Monitor

**Python** app that tails the **Vintage Story** client log, tracks **connect queue position**, estimates **wait time**, and raises alerts at configurable thresholds. The UI is a **local web app** on `127.0.0.1` (embedded **pywebview** window when available; otherwise your browser, or **`--web-browser`**). Inline KPI edits, canvas graph, PNG/TSV copy, spotlight tour (`starlette` + `uvicorn`; **pywebview** on Python 3.13 and older in `requirements.txt`).

**Product and UX:** [`docs/DESIGN.md`](docs/DESIGN.md). **Web parity:** [`docs/UI-PARITY.md`](docs/UI-PARITY.md), [`docs/UI-UX-PARITY.md`](docs/UI-UX-PARITY.md), [`docs/WEB-PLATFORM.md`](docs/WEB-PLATFORM.md). **Architecture notes:** [`docs/real-life-ui-patterns.md`](docs/real-life-ui-patterns.md).

<img width="1916" height="1072" alt="VS Queue Monitor screenshot" src="https://github.com/user-attachments/assets/648649c3-264c-4880-9e80-7a46efc4d746" />

## Disclaimer (read this)

**No warranty — use at your own risk.** **Not affiliated with Vintage Story** or its developers. You must validate paths, alerts, ETAs, and time-sensitive decisions yourself.

- **Work in progress:** Features, UI, saved settings, and behavior can change at any time.
- **AI-assisted code:** Much of this codebase was produced or refactored with AI / coding assistants. Validate paths, alerts, ETAs, and log interpretation yourself.

## Quick start

Install first—details about libraries and behavior are in [Runtime requirements](#runtime-requirements) below.

### What you need first

- **Python 3.10+** on your PATH (`python`, `py`, or `python3`) for the main Windows/macOS/Linux line below (the “no Python yet” Windows one-liner installs Python for you).
- **Git** (the bootstrap flow clones this repo; usually already installed).
- **Network** access to GitHub (to download the bootstrap script and clone).

**One command** — paste a single line into **Command Prompt** or **Win+R** (Windows) or your terminal (macOS/Linux). Each line tries your **Downloads** folder first (usual place for fetched files); **nothing creates that folder**—if it is missing, the line falls back to your profile (`%USERPROFILE%` / `$HOME`). Then it clones the app (default `%USERPROFILE%\vs-queue-monitor` on Windows, `~/vs-queue-monitor` elsewhere), creates `.venv`, installs dependencies, adds a **Desktop** shortcut on Windows, and asks whether to start the app when stdin is a TTY (**piped** one-liners start the monitor immediately after install).

**Windows** (`curl` is included on Windows 10+; use **`python`** instead of **`py -3`** if you do not have the `py` launcher — edit the last part of the line):

```bat
cmd /c "(cd /d \"%USERPROFILE%\Downloads\" 2>nul || cd /d \"%USERPROFILE%\") && curl -fsSL https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap.py | py -3 -"
```

**If Python is not installed yet**, use this one line instead (downloads and runs the helper into Downloads when that folder exists; opens the Python installer page when needed):

```bat
cmd /c "(cd /d \"%USERPROFILE%\Downloads\" 2>nul || cd /d \"%USERPROFILE%\") && curl -fsSL https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap-windows.cmd -o vs-queue-monitor-bootstrap.cmd && call vs-queue-monitor-bootstrap.cmd"
```

**macOS / Linux:**

```bash
(cd "$HOME/Downloads" 2>/dev/null || cd "$HOME") && curl -fsSL https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap.py | python3 -
```

Optional: install only, no launch — `VS_QUEUE_MONITOR_SKIP_RUN=1` before the command. Skip the Desktop shortcut — `VS_QUEUE_MONITOR_NO_DESKTOP_SHORTCUT=1` (Windows). Override install folder — `VS_QUEUE_MONITOR_HOME` (see **Bootstrap** below).

`python bootstrap.py` accepts the same arguments as `monitor.py` (e.g. `--path "%APPDATA%\VintagestoryData"`, `--web-browser`).

### Already cloned or developing

```bash
pip install -r requirements.txt
python monitor.py
```

Same as `python -m vs_queue_monitor`. Default: web UI on `127.0.0.1`. In the header, the **folder** and **log file** icons open a native picker on the machine running Python (Tk); click the path status or paste in the prompt to set a path. **Saving the path** (picker, prompt, or restore banner) **restarts monitoring** so the resolved log file and queue **session** list update.

| | |
|--|--|
| Windows | `vs-queue-monitor.cmd` / `Run VS Queue Monitor.bat` · `Win+R` → `vs-queue-monitor` if the repo directory is on user **`Path`** · else `"…\vs-queue-monitor\vs-queue-monitor.cmd"` |
| macOS / Linux | `./run-vs-queue-monitor.sh` or `python3 monitor.py` |

### Windows: Run dialog (Win+R) after install

**If Python is not installed** — `vs-queue-monitor.cmd`, `Run VS Queue Monitor.bat`, and `bootstrap-windows.cmd` print a short message, open the **Python for Windows** download page in your browser, and exit after you press a key. Install **Python 3.10+**, enable **Add python.exe to PATH** during setup (or add it later), then run again.

**If Python is already installed** — from a full clone (or after bootstrap has run once):

1. Press **Win+R** (Run).
2. **Paste** the launcher: either `vs-queue-monitor` (if the repo folder is on your user **Path**) or the full path to `vs-queue-monitor.cmd`, e.g. `C:\Users\You\vs-queue-monitor\vs-queue-monitor.cmd`.
3. Press **Enter**.
4. **Wait** — first launch may create `.venv` and install packages (can take a minute).
5. The **app opens** (embedded window when `pywebview` is available, otherwise your browser).

**Bootstrap** — default clone `~/vs-queue-monitor`; `VS_QUEUE_MONITOR_HOME` overrides. Forks: `VS_QUEUE_MONITOR_REPO`, `VS_QUEUE_MONITOR_BRANCH`. Non-`main` branch: fix the raw URL path (e.g. `feature%2Funified-approach`). For `bootstrap-windows.cmd`, set `VS_QUEUE_MONITOR_BOOTSTRAP_URL` to the raw `bootstrap.py` URL on your branch if needed.

**Alternatives (save `bootstrap.py` first)**

```bash
(cd "$HOME/Downloads" 2>/dev/null || cd "$HOME") && curl -fsSL https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap.py -o bootstrap.py && python3 bootstrap.py
```

**Windows (PowerShell, one line)**

```powershell
$d = Join-Path $env:USERPROFILE 'Downloads'; if (Test-Path $d) { Set-Location $d } else { Set-Location $env:USERPROFILE }; Invoke-WebRequest -Uri "https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap.py" -OutFile bootstrap.py; python bootstrap.py
```

After a git clone you can run `bootstrap-windows.cmd` instead: it checks for `py` / `python` before piping to `bootstrap.py` (same behavior as piping `bootstrap.py` when Python is present).

Log path: folder above or containing `client-main.log` — [Pointing at the log](#pointing-at-the-log).

## Runtime requirements

These apply **after** you install (via bootstrap or `pip install -r requirements.txt`). For the fastest path to a running app, use [Quick start](#quick-start) above.

- **Python 3.10+** — same bar as [What you need first](#what-you-need-first); the app and tests target this baseline.
- **Starlette + uvicorn** — `pip install -r requirements.txt`; serves the **default** web UI on `127.0.0.1`.
- **Desktop alerts** use the standard **Notifications** API (`Notification.requestPermission()` + `new Notification()`). The header **bell** is **green** when Warning popup is on and the browser allowed notifications, **amber** when Warning popup is on but permission is still needed, and **crossed** when alerts are off in Settings, blocked in the browser, or unavailable. Click it to allow or send a test (`http://127.0.0.1:…`). **Threshold** toasts and system notifications use the **same human-readable text** as the engine (not just a timestamp). **In-app toasts** appear whenever a threshold fires; **system tray** banners use the same **standard web Notifications API** as any site (`Notification.requestPermission()` from the **bell**, then `new Notification()` when alerts fire), plus **Settings → Warning popup** and OS notification settings. On **Windows**, embedded **WebView2** (Chromium) attaches a **permission** handler so the host does not block requests before you allow them. If permission is granted but nothing appears, check **Windows Settings → System → Notifications** for **Edge WebView2** / the app host. Install the [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) if the window fails to start. Use **`python monitor.py --web-browser`** if you prefer your installed browser. Optional: set **`VS_QUEUE_MONITOR_WEBVIEW_GUI`** to change the pywebview backend (default `edgechromium` on Windows; legacy: **`VSQM_WEBVIEW_GUI`**).
- **pywebview** — pulled automatically on **Python 3.13 and older** for the embedded desktop shell. On **Python 3.14+**, `requirements.txt` skips it until wheels exist; use **`--web-browser`** or `pip install pywebview` when a build is available for your Python.

**Dependency policy:** Prefer the **Python standard library** when it fits the job. Beyond that, use **well-maintained, permissively licensed open-source** packages on PyPI (the local UI is **Starlette** + **uvicorn**; optional embedded shell **pywebview**). New runtime dependencies belong in `requirements.txt` and, when they affect install or how users run the app, in this README in the same change. The web client is **plain JS** (no npm build for the default flow) with **vendored open-source** bundles under [`vs_queue_monitor/web/static/vendor/`](vs_queue_monitor/web/static/vendor/) (e.g. **Day.js**, MIT, for date/time formatting); see `vendor/README.md` for versions.

### Default web UI

`http://127.0.0.1:8765/` — **embedded webview** when available (preferred on Windows/macOS/Linux desktops); otherwise your **default browser**. On **Windows**, the embedded path opens a **second console window** that runs the HTTP server (uvicorn logs, **Ctrl+C** stops the server there) and a separate **pywebview** window for the UI—so you always see server output. That subprocess **sets its working directory to the app install folder** so the server still starts if you launched `monitor.py` from elsewhere (Explorer, Run dialog, another folder). If the server **crashes on startup** (missing dependency, import error), that console stays open with **Press any key to continue…** so you can read the traceback. Set **`VS_QUEUE_MONITOR_DISABLE_SPLIT_CONSOLE=1`** (legacy: `VSQM_DISABLE_SPLIT_CONSOLE`) to keep a single process (uvicorn background thread + webview) like other platforms. **`--web-browser`** uses one terminal for the server and opens the UI in an external browser. **`--web-port`** / **`VS_QUEUE_MONITOR_WEB_PORT`**. **Ctrl+C** in the foreground process stops what that process owns. **`--web`** is a no-op alias for scripts.

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

The web client supports **inline editing** (✎ on poll interval, rolling window, thresholds — popovers are **fixed** to the viewport so they stay on top and are not clipped by the scrollable KPI strip), **Copy graph as PNG**, **Copy graph (TSV)**, **session Stats** (same scope as the Session graph dropdown) with **Copy stats**, **Copy history**, and a **guided spotlight tour** (runs once until completed; stored as `tutorial_done` in config). Layout and controls follow a single dark theme with consistent spacing, focus rings, and modal/dialog semantics. On **wide** windows the **KPI** row uses **seven equal-width** tiles; narrower widths reflow. **KPI** tiles use a muted em dash when a value is not available (**hover** for a short hint). The chart toolbar keeps **Session**, log activity, and **Y-scale / Live / export** in one left-to-right flow (no large empty gap). On **wide** layouts the **log path** block is **right-aligned** (capped width) next to that toolbar. **Info** and **History** use **equal-width** columns on wide layouts. **KPI** rate header stays on one line (ellipsis if needed) so labels align. **Keyboard** (when not typing in a field): **Space** start/stop, **o** settings, **F1** help, **c** graph TSV, **v** copy session history. Those shortcuts are disabled while a modal, the tour, or the restore banner is open.

### Without auto-start

```bash
python monitor.py --no-start
```

## Project layout

| Path | Role |
|------|------|
| `vs_queue_monitor/core.py` | Parsing, config, log I/O — no UI |
| `vs_queue_monitor/engine.py` | Shared monitor logic |
| `vs_queue_monitor/web/` | Local Starlette app + static client (only UI) |
| `vs_queue_monitor/cli.py` | Web UI; `--web`, `--web-browser`, `--path`, `--no-start` |
| `monitor.py` | Entrypoint |
| `vs-queue-monitor.cmd` | Windows: launcher for **Win+R** / PATH; runs `monitor.py` (uses `.venv` if present) |
| `vsqm.cmd` | Compatibility shim — calls **`vs-queue-monitor.cmd`** |
| `Run VS Queue Monitor.bat` | Windows: double-click; delegates to **`vs-queue-monitor.cmd`** |
| `bootstrap-windows.cmd` | Windows: `curl` + pipe to Python; **Win+R** one-liner in README; warns if Python missing |
| `run-vs-queue-monitor.sh` | macOS/Linux: run from terminal (uses `.venv` if present) |
| `bootstrap.py` | One-file launcher: clone (if needed), venv, `pip install`, run `monitor.py` |
| `requirements-dev.txt` | Optional: **pytest** + **Playwright** for UI smoke tests |
| `tests/` | Playwright tests against the local web server |

### UI tests (Playwright)

Browser smoke tests spin up the same **Starlette** app used in production (no mocks) and open it in **Chromium**:

```bash
pip install -r requirements-dev.txt
playwright install chromium
python -m pytest tests/
```

Run **`python -m pytest tests/ --headed --slowmo 400`** to watch the browser. With the app already running (`python monitor.py`), use **`playwright codegen http://127.0.0.1:8765/`** to record steps and paste generated selectors.

**Layout checks** (`tests/test_ui_visual.py`): several **viewport widths** (mobile through desktop), **no horizontal document overflow**, **top bar** overflow check, **information architecture** (KPI labels, graph canvas, **Info** / **History** titles), and a **long log path** via `POST /api/config` to ensure the path summary still fits. **`tests/test_notifications_ui.py`** checks the **bell** + standard web notification flow (Chromium’s `Notification` is stubbed in tests so permission is deterministic). For **full-page PNGs** under pytest’s temp dir, run with **`VS_QUEUE_MONITOR_PLAYWRIGHT_SCREENSHOTS=1`** (legacy: `VSQM_PLAYWRIGHT_SCREENSHOTS`).

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
| `--path PATH` | Initial **Logs folder** (directory; resolves to `client-main.log` inside) |
| `--no-start` | Open without auto-starting monitoring |

## Install Python

### Windows

1. Install **Python** from [python.org](https://www.python.org/downloads/) (enable PATH).
2. In the project folder: `pip install -r requirements.txt` then `python monitor.py` (embedded web UI by default).

### macOS

Install Python from [python.org](https://www.python.org/downloads/macos/) or Homebrew.

### Linux (Debian / Ubuntu)

```bash
sudo apt update && sudo apt install python3
pip install -r requirements.txt
python3 monitor.py
```

(`python3 monitor.py` starts the **embedded web UI** by default.)

## Log file (game output)

The client log lines look like:

- `Client is in connect queue at position: N`
- `Your position in the queue is: N`

## Behavior (summary)

Detailed intent is in [`docs/DESIGN.md`](docs/DESIGN.md). This section is a short operational summary.

### Dashboard

- **Header:** Log source row with folder/file pickers; clicking the path summary opens an **in-app path dialog** (no browser `prompt`). On **narrow widths** the bar **stacks** (title row, then path, then notifications) and the path **truncates** with ellipsis instead of overflowing. **Help** (**?**) lists typical Vintage Story data paths, keyboard shortcuts, and where the config file is stored. **Escape** closes open dialogs; closing Help or Settings moves keyboard focus back to **?** or **⚙** (opening them focuses the primary control inside the dialog). Open dialogs keep **Tab** cycling within the dialog.
- **KPIs:** Position (including **0** when past connect-queue wait per tail rules), status, rolling rate, warning thresholds, elapsed, ETA, progress.
- **Graph:** Step chart of queue position vs time for the **current queue session**; log/linear Y where available. While monitoring, **each poll** appends a sample (so flat segments show “heartbeat” time at unchanged position, not only log-line updates). The canvas tracks layout size and device pixel ratio on each refresh and stays within the card on narrow widths. With **no samples yet**, the plot shows a short **two-line** empty-state message. A **one-line** hint sits under the chart; **tap or hover** shows a **tooltip** with time, position, and change vs the previous sample (rate when position moved).
- **Info / History:** Two columns with matching compact **INFO** / **HISTORY** titles (then the details grid and session log); optional per-step queue lines when **Log every position change** is on (default **on**).

### Queue semantics

- **Completed** requires **post-queue** lines after the last queue position line in the tail — not merely reaching position `1`.
- **Interrupted** freezes rate/elapsed display appropriately while still polling when useful.

### Alerts

- **Thresholds:** comma-separated positions (default `10, 5, 1`); fire on **downward** crossings, once per threshold per run.
- **Completion:** when the tail shows past-queue activity after the last queue line.
- **Sounds / popups / OS notifications:** configurable per channel in Settings.

### Settings

- Stored in **`config.json`** (see `vs_queue_monitor.core.get_config_path()`).

### Without Git (source archive)

Download the repo as ZIP or tarball from GitHub, extract, then `pip install -r requirements.txt` and `python monitor.py` as above.

## License / game

Independent tool for reading **your** client log. Not affiliated with Vintage Story or its authors.
