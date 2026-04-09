# VS Queue Monitor

Desktop app (Python + Tkinter) that tails the **Vintage Story** client log, tracks **connect queue position**, estimates **wait time**, and raises **alerts** when you cross configurable thresholds (popup + optional sound on Windows). Config and sources use the short id **`vs-queue-monitor`**.

## Disclaimer (read this)

**No warranty — use at your own risk.** **Not affiliated with Vintage Story** or its developers. You must validate paths, alerts, ETAs, and time-sensitive decisions yourself.

- **Work in progress:** Features, UI, saved settings, and behavior can change at any time. Expect bugs and incomplete polish.
- **AI-assisted code:** A large share of this project was written or refactored with AI / coding assistants. That means **more risk of subtle mistakes** (logic, edge cases, platform quirks). You are responsible for validating paths, alerts, ETAs, and anything safety- or time-sensitive.
- **Not official:** Not affiliated with Vintage Story or its developers. **No warranty** — use at your own risk.


## Requirements

- **Python 3.10+** (any recent 3.x with Tkinter)
- **Tkinter** — see [Install Python and Tkinter](#install-python-and-tkinter) below

No third-party pip dependencies.

## Install Python and Tkinter

### Windows

1. Install **Python** from [python.org](https://www.python.org/downloads/) (64-bit is fine).
2. In the installer, enable **“Add python.exe to PATH”** and use the default options so **tcl/tk** (needed for the GUI) is included.
3. Open **Command Prompt** or **PowerShell**, go to the folder that contains `monitor.py`, and run:

   ```powershell
   python monitor.py
   ```

   If `python` is not found, try `py monitor.py` (Windows Python launcher).

### macOS

1. Install **Python 3** from [python.org](https://www.python.org/downloads/macos/) **or** with Homebrew (`brew install python`).
2. The python.org macOS build normally includes **Tkinter**. If you use Homebrew-only Python and the window fails to open, install a Tk-enabled build (for example `brew install python-tk` where available, or prefer the official installer).
3. In **Terminal**:

   ```bash
   cd /path/to/vs-queue-monitor
   python3 monitor.py
   ```

### Linux (Debian / Ubuntu / derivatives)

1. Install Python and Tk:

   ```bash
   sudo apt update
   sudo apt install python3 python3-tk
   ```

2. Run:

   ```bash
   cd /path/to/vs-queue-monitor
   python3 monitor.py
   ```

### Linux (Fedora / RHEL-like)

```bash
sudo dnf install python3 python3-tkinter
cd /path/to/vs-queue-monitor
python3 monitor.py
```

(Package names may differ slightly; search your package manager for **python** + **tk**.)

## Run (all platforms)

From the directory that contains `monitor.py`:

| Platform   | Typical command   |
|-----------|-------------------|
| Windows   | `python monitor.py` or `py monitor.py` |
| macOS/Linux | `python3 monitor.py` |

By default the app **starts monitoring** when it opens (if the log path resolves). To open the UI **without** auto-start:

```bash
python3 monitor.py --no-start
```

(On Windows, use `python` instead of `python3` if that is what works on your machine.)

### Pointing at the log

You can pass a **file** or a **folder** to search for `client-main.log`:

**Windows (Command Prompt / PowerShell)**

```powershell
python monitor.py --path "%APPDATA%\VintagestoryData\client-main.log"
python monitor.py --path "C:\path\to\VintagestoryData"
```

**macOS / Linux (bash)**

```bash
python3 monitor.py --path "$HOME/Library/Application Support/VintagestoryData/client-main.log"
python3 monitor.py --path "$HOME/.config/VintagestoryData/client-main.log"
```

Exact Vintage Story data locations depend on your install; use the **Log location** field in the app if unsure.

## Log file

The game writes queue lines similar to:

- `Client is in connect queue at position: N`
- `Your position in the queue is: N`

The default path hint in the UI targets Windows (`%APPDATA%/VintagestoryData/...`). On macOS or Linux, browse to your Vintage Story data folder or paste the full path to `client-main.log`. If you pass a **directory**, the app searches for `client-main.log` (and a few fallbacks) under common layouts.

## Features

### Window layout

- Three vertical **panes** — **Queue graph** (top), **Status** (middle), **History** (bottom) — separated by **draggable sashes**.
- **Status** and **History** can be **collapsed** to a thin header bar (chevron + title); the app refits pane heights so empty bands do not linger.
- Dark, **tooltip-heavy** UI (hover for control explanations).

### Log location and resolution

- **Log location** field plus **Browse file** / **Browse folder** to pick a path. Paths support environment tokens (e.g. `%APPDATA%` on Windows, `~` / `$HOME`).
- **Direct file:** any readable path to a log file is used as-is.
- **Folder:** resolves to `client-main.log` in common locations (`Logs/`, `logs/`), then falls back to searching for matching log filenames by modification time.
- **Resolved path** is shown in the Status section when monitoring.

### Monitoring

- **Play / Stop** toggles tailing the log on an interval (**poll**, configurable in Settings).
- On start, the app can **seed the graph** from a larger tail of the log (with a loading indicator) so you see recent queue history immediately.
- **Timer (~10 Hz)** refreshes elapsed time, remaining ETA, and rate between log polls so values feel live.

### Queue graph pane

- **KPI strip (one header row, one value row):** **Position**, **Status** (connection/monitoring state), **Rate** (minutes per position), **Elapsed**, **Remaining** (ETA), **Progress** (thin bar: share of estimated total wait elapsed; full at queue front).
- **Chart:** step plot of queue position vs time; hover near the line for timestamp and position.
- **Y → log / Y → linear** toggles **log-scale** vs **linear** vertical axis (helps when position spans a wide range).
- Graph preferences persist (see **Configuration file**).

### Status pane (collapsible)

- Click the **Status** header bar or chevron to expand or collapse details.
- When expanded, pane height fits **full content** (path, labels, wrapping text).
- Shows **Last change**, **Last threshold alert**, and **Resolved log path** (and related labels).

### History pane (collapsible)

- Click **History** to show or hide the scrollable session log.
- Logs path changes, queue updates (optional **every position change**), alerts, seed messages, errors, and warnings.

### Alerts

- **Comma-separated thresholds** (default `10, 5, 3, 2, 1`): an alert can fire when your position **crosses downward** through each threshold.
- **Once per threshold per queue run** until the run resets (log boundary / new session / segmentation rules).
- **Minimum interval** between popup/sound alerts to reduce duplicate fires from noisy logs.
- **Popup** (optional): small always-on-top window with dismiss; auto-closes after a timeout.
- **Sound** (optional): default uses the **system notification sound** (Windows registry aliases / `MessageBeep`, macOS **Glass**-style sounds in `/System/Library/Sounds`, Linux **freedesktop** / common theme files via `paplay` when available). If that fails, a single terminal **bell**. You can set a custom **Sound file** in Settings instead.

### ETA, rate, and progress

- **Remaining** uses position and a **speed model**: empirical throughput from recent log updates when possible, otherwise a **recency-weighted** estimate from the prediction **window** (points).
- **Minutes per position** is shown as **Rate**; can be **capped** using dwell logic so optimistic rates do not jump until you have waited long enough at the current position.
- **Progress** bar uses elapsed ÷ (elapsed + estimated remaining) when both are known; **100%** at queue front (position ≤ 1); empty when interrupted or ETA unknown.
- **Stale queue detection:** if no new queue lines arrive for too long relative to the expected update cadence, the run can be treated as **Interrupted**.

### Connection and status line

The status string reflects tail-of-log classification, for example:

- **Monitoring** — queue line present, in queue (`position > 1`).
- **Completed** — reached front (position ≤ 1); not overwritten by noisy “connecting” lines after that.
- **Interrupted** — definitive disconnect / stale queue; **elapsed time freezes** but the log **keeps** being read.
- **Reconnecting…** / **Connecting…** / **Waiting for log file** / **Error** as appropriate.
- **Log silence:** no file growth for a long interval can show reconnect-style status (with guards so **Completed** is not clobbered when you are already at the front).

### New queue after interrupt

- If a **new queue run** appears in the log while in **Interrupted**, a dialog can offer to **load** it and **re-seed** the graph and alert state for that run.

### Settings (gear)

- **Thresholds** (comma-separated positions).
- **Poll (s)** — seconds between log reads.
- **Alert popup** / **Alert sound** / optional **Sound file** path (**Browse…**, **Preview**) / **Log every position change**.
- **Window (points)** — rolling **prediction window** size for weighted rate / ETA.
- **Reset defaults** — restores built-in defaults and clears local session state tied to that flow.
- **Close** or **Escape** saves config (same debounced persistence as the rest of the app).

### Keyboard shortcuts

- **Space** — start/stop monitoring (ignored when typing in a text field).
- **Ctrl+M** — start/stop monitoring.

### Command-line interface

| Argument | Meaning |
|----------|---------|
| `--path PATH` | Initial log file or folder (same rules as **Log location**). |
| `--no-start` | Open the UI **without** auto-starting monitoring. |

### Tooltips

- Most controls on the main window have **hover tooltips** (short explanations).

## Configuration file

Saved automatically (debounced, ~450 ms after a change) when you change options, path text, or window geometry:

| OS | Path |
|----|------|
| Windows | `%APPDATA%\vs-queue-monitor\config.json` |
| Linux/macOS | `$XDG_CONFIG_HOME/vs-queue-monitor/config.json` or `~/.config/vs-queue-monitor/config.json` |

If you used an older build, settings may load once from `%APPDATA%\vs-q-monitor\` (Windows) or `~/.config/vs-q-monitor/` (Unix) and are then saved under the new folder name.

Typical keys:

| Key | Purpose |
|-----|---------|
| `source_path` | Log location string |
| `alert_thresholds` | Comma-separated thresholds (default `10, 5, 3, 2, 1`) |
| `poll_sec` | Poll interval in seconds |
| `avg_window_points` | Prediction window size (points) |
| `show_log` | History pane expanded (content visible) |
| `show_status` | Status pane expanded (content visible) |
| `graph_log_scale` | Graph Y axis: log vs linear |
| `popup_enabled` | Threshold alert popup |
| `sound_enabled` | Threshold alert sound |
| `alert_sound_path` | Alert sound file path (defaults to the same OS file the app uses for built-in playback) |
| `show_every_change` | Log every queue position line vs only changes |
| `window_geometry` | Last main window size/position |
| `version` | App version string written at save time |

## Development

```bash
python -m py_compile monitor.py
```

## License / game

This project is an independent tool for reading **your** client log. It is not affiliated with Vintage Story or its authors.
