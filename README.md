# VS Queue Monitor

Desktop app (Python + Tkinter) that tails the **Vintage Story** client log, tracks **connect queue position**, estimates **wait time**, and raises **warning** alerts at **configurable thresholds**, plus optional **queue completion** notices at the front (on/off only — not threshold-based). Config and sources use the short id **`vs-queue-monitor`**.

## Disclaimer (read this)

**No warranty — use at your own risk.** **Not affiliated with Vintage Story** or its developers. You must validate paths, alerts, ETAs, and time-sensitive decisions yourself.

- **Work in progress:** Features, UI, saved settings, and behavior can change at any time. Expect bugs and incomplete polish.
- **AI-assisted code:** A large share of this project was written or refactored with AI / coding assistants. That means **more risk of subtle mistakes** (logic, edge cases, platform quirks). You are responsible for validating paths, alerts, ETAs, and anything safety- or time-sensitive.
- **Not official:** Not affiliated with Vintage Story or its developers. **No warranty** — use at your own risk.

## Requirements

- **Python 3.10+** (any recent 3.x with Tkinter)
- **Tkinter** — see [Install Python and Tkinter](#install-python-and-tkinter) below

No third-party pip dependencies.

## Quick start

You need [Python 3.10+ with Tkinter](#install-python-and-tkinter). No `pip` install step.

### Without Git

Fetches **latest `main`** as a GitHub source archive into **Downloads**; unpacked folder: `vs-queue-monitor-main`.

**macOS, Linux, Git Bash**

```bash
cd "$HOME/Downloads" && curl -L https://github.com/ShubiMaja/vs-queue-monitor/archive/refs/heads/main.tar.gz | tar xz
```

```bash
cd "$HOME/Downloads/vs-queue-monitor-main" && python3 monitor.py
```

**Windows PowerShell** (Windows 10+, built-in `tar`)

```powershell
Set-Location $env:USERPROFILE\Downloads; Invoke-WebRequest -Uri "https://github.com/ShubiMaja/vs-queue-monitor/archive/refs/heads/main.tar.gz" -OutFile "vsqm.tar.gz"; tar -xf vsqm.tar.gz
```

```powershell
Set-Location $env:USERPROFILE\Downloads\vs-queue-monitor-main; python monitor.py
```

On Windows, use `py` instead of `python` if needed. For a **tagged release**, use that tag in the archive URL, e.g. `https://github.com/ShubiMaja/vs-queue-monitor/archive/v1.0.0.tar.gz`.

**No terminal:** GitHub → **Code → Download ZIP** → extract the folder that contains `monitor.py` (often `vs-queue-monitor-main`) → `python3 monitor.py` or `python monitor.py`.

### With Git

```bash
git clone https://github.com/ShubiMaja/vs-queue-monitor.git && cd vs-queue-monitor && python3 monitor.py
```

On Windows use `python` or `py` instead of `python3`. With SSH: `git@github.com:ShubiMaja/vs-queue-monitor.git`.

### Maintainers: distribution without Git

GitHub serves **source archives** for public repos; no separate host.

- Keep **owner/repo**, **default branch**, and any **tag** URLs in this README accurate; update if the default branch is renamed.
- **Public repo** is required for anonymous `curl`/browser downloads without tokens.
- **Releases:** tag `vX.Y.Z`, publish a [Release](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository), tarball `https://github.com/ShubiMaja/vs-queue-monitor/archive/vX.Y.Z.tar.gz`. Optional: attach ZIP/installers or CI artifacts.
- **PyPI** or **frozen binaries** (PyInstaller, Nuitka, …) are optional extras.

**Default:** document **archive URLs** + **tagged Releases**; add PyPI or frozen builds only if we want them.

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

- **Warning thresholds** — comma-separated positions (default `10, 5`): **warning** popup/sound can fire when you **cross downward** through each value. **Once per value per queue run** until the run resets (log boundary / new session / segmentation rules).
- **Completion** — **not** threshold-based: it always applies when you **reach the queue front** (position ≤1). You only choose **on/off** for completion **popup** and/or **sound** (plus optional completion **sound file**). There is no comma-separated completion threshold list.
- **Minimum interval** between **warning** popup/sound alerts to reduce duplicate fires from noisy logs.
- **Warning popup** (optional): always-on-top window for **threshold crossings**; auto-closes after a timeout.
- **Completion popup** (optional): distinct window at queue front (≤1); **enable/disable only** — same trigger every time.
- **Warning sound** (optional): plays on **warning** thresholds; built-in default is one file per OS (e.g. `Windows Background.wav`, `Basso.aiff`, `dialog-warning.oga`), resolved like other system media paths, then registry/`MessageBeep`/bell. Custom path in Settings.
- **Completion sound** (optional): **on/off** at queue front (≤1); one default per OS (e.g. `tada.wav`, `Hero.aiff`, `complete.oga`). Custom path in Settings.

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

- **Polling** — **Poll (s)** between log reads.
- **Warning Alerts** — comma-separated **thresholds**, **Warning popup** / **Warning sound** / **Warning sound file**.
- **Completion Alerts** — **on/off only** at queue front (≤1, no threshold list); **Completion popup**, **Completion sound**, **Completion sound file**.
- **History** — **Show History panel** (expanded log vs header-only) and **Log every position change** (verbose vs milestones-only lines).
- **Prediction** — **Window (points)**: rolling window size for weighted rate / ETA.
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
| `alert_thresholds` | Warning thresholds only, comma-separated (default `10, 5`); not used for completion |
| `poll_sec` | Poll interval in seconds |
| `avg_window_points` | Prediction window size (points) |
| `show_log` | History pane expanded (content visible) |
| `show_status` | Status pane expanded (content visible) |
| `graph_log_scale` | Graph Y axis: log vs linear |
| `popup_enabled` | Warning (threshold) popup |
| `completion_popup_enabled` | Queue completion (front) popup |
| `sound_enabled` | Warning (threshold) sound enabled |
| `alert_sound_path` | Warning sound file path |
| `completion_sound_enabled` | Queue completion (position ≤1) sound enabled |
| `completion_sound_path` | Completion sound file path |
| `show_every_change` | Log every queue position line vs only changes |
| `window_geometry` | Last main window size/position |
| `version` | App version string written at save time |

## Development

```bash
python -m py_compile monitor.py
```

## License / game

This project is an independent tool for reading **your** client log. It is not affiliated with Vintage Story or its authors.
