# VS Queue Monitor

Desktop app (Python + Tkinter) that tails the **Vintage Story** client log, tracks **connect queue position**, estimates **wait time**, and raises **warning** alerts at **configurable thresholds**, plus optional **queue completion** notices when the log suggests you are **past the connect queue** (connecting / loading — on/off only — not threshold-based). Config and sources use the short id **`vs-queue-monitor`**.

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

By default the app **starts monitoring** when it opens (if the **Logs folder** path exists). If no client log file is there yet, status stays **Waiting for log file** until it appears. To open the UI **without** auto-start:

```bash
python3 monitor.py --no-start
```

(On Windows, use `python` instead of `python3` if that is what works on your machine.)

### Pointing at the log

Pass a **folder** (Vintage Story data directory, or a folder that contains the client log). The app resolves the correct log **filename** inside that tree (e.g. `client-main.log`) — you do not pick a `.log` file in the UI.

**Windows (Command Prompt / PowerShell)**

```powershell
python monitor.py --path "%APPDATA%\VintagestoryData"
```

**macOS / Linux (bash)**

```bash
python3 monitor.py --path "$HOME/Library/Application Support/VintagestoryData"
python3 monitor.py --path "$HOME/.config/VintagestoryData"
```

Exact Vintage Story data locations depend on your install; use **Browse…** on **Logs folder** in the app if unsure. The default is a **folder** path (`%APPDATA%/VintagestoryData` on Windows), not a `.log` file. If an older saved setting still pointed at a **file**, the app rewrites it to that file’s **parent folder** in the field (and config) on startup. Resolution **prefers `client-main.log`** when present, then other matching names.

## Log file

The game writes queue lines similar to:

- `Client is in connect queue at position: N`
- `Your position in the queue is: N`

The default path hint in the UI targets Windows (`%APPDATA%/VintagestoryData`). On macOS or Linux, browse or paste your Vintage Story **data** folder. The app searches for `client-main.log` (and a few fallbacks) under common layouts.

## Features

### Window layout

- Three vertical **panes** — **Graph** (top), **Info** (middle), **History** (bottom) — separated by **draggable sashes**.
- **Info** and **History** can be **collapsed** to a thin header bar (chevron + title); the app refits pane heights so empty bands do not linger.
- Dark, **tooltip-heavy** UI (hover for control explanations).

### Logs folder and resolution

- **Logs folder** field plus **Browse…** (folder picker only). The folder must **exist**; it does **not** need to contain a log file yet (e.g. before the first Vintage Story run). Paths support environment tokens (e.g. `%APPDATA%` on Windows, `~` / `$HOME`).
- When you **Play**, the app **searches** under that folder for `client-main.log` / `client.log` in common locations (`Logs/`, `logs/`, etc.), then filenames matching `*client-main*.log` or `*client*.log`. It does **not** pick unrelated `*.log` files. If none exist yet, monitoring still starts and status shows **Waiting for log file** until one appears.
- **Resolved path** (the actual log file opened) appears in the **Info** section once a file is found (along with timing and rate details below).

### Monitoring

- **Play / Stop** toggles tailing the log on an interval (**poll**, configurable in Settings).
- On start, the app can **seed the graph** from a larger tail of the log (with a loading indicator) so you see recent queue history immediately.
- **Elapsed** time is anchored to the log: it uses the first **connecting / connection attempt** line in the current queue session when that line appears in the scanned log, otherwise the first **queue position** line in the graph. Reaching the **front** (position ≤1) freezes elapsed using **log line timestamps**, not the moment you opened the monitor.
- **Timer (~10 Hz)** refreshes elapsed time, remaining ETA, and rate between log polls so values feel live.

### Graph pane (top)

- **KPI strip (one header row, one value row):** **Position** (queue index from the log, or **0** when a post-queue line shows you are **not** still waiting in queue — e.g. loading mods), **Status** (connection/monitoring state — not the Info panel name), **Rate** (**Last N** — minutes per position from the prediction **window** in Settings, e.g. `Last 10: 6.20 min/pos`), **Warnings** (configured threshold numbers; each value appears muted once your position is at or below that threshold, or after that alert fired), **Elapsed**, **EST. REMAINING** (ETA), **Progress** (thin bar: share of estimated total wait elapsed; **100%** at **position 0**).
- **Chart:** step plot of queue position vs time (**0** = past queue wait); hover near the line for timestamp and position.
- **Y → log / Y → linear** toggles **log-scale** vs **linear** vertical axis (helps when position spans a wide range).
- Graph preferences persist (see **Configuration file**).

### Info pane (collapsible)

- Click the **Info** header bar or chevron to expand or collapse details.
- When expanded, pane height fits **full content** (path, labels, wrapping text).
- Shows **Last change**, **Last threshold alert**, **Resolved log path**, and **Global Rate** — average minutes per position over every forward queue step in the **full** graph (all segments), distinct from the KPI **Rate** line which uses the prediction window and dwell caps.

### History pane (collapsible)

- Click **History** to show or hide the scrollable session log.
- Logs path changes, optional **queue position lines** (only when **Log every position change** is on), alerts, seed messages, errors, and warnings.

### Alerts

- **Warning thresholds** — comma-separated positions (default `10, 5, 1`): **warning** popup/sound can fire when you **cross downward** through each value. **Once per value per queue run** until the run resets (log boundary / new session / segmentation rules).
- **Completion** — **not** threshold-based: it fires when a **post-queue** line appears **after** the last **connect queue position** line in the log tail (e.g. *Loading and pre-starting client side mods*, download — **not** only full “connected”; and not when you first hit position `1`, which can still mean a long wait). You only choose **on/off** for completion **popup** and/or **sound** (plus optional completion **sound file**). There is no comma-separated completion threshold list. If your client build does not log matching lines, completion may not fire. Opening the monitor when the log **already** shows that past-queue state (a finished wait) does **not** fire completion again — only a **new** transition to that state while monitoring does.
- **Minimum interval** between **warning** popup/sound alerts to reduce duplicate fires from noisy logs.
- **Warning popup** (optional): always-on-top window for **threshold crossings**; auto-closes after a timeout.
- **Completion popup** (optional): distinct window when the log shows connect phase after the queue, with **Get ready to connect!** copy; **enable/disable only** — same trigger every time.
- **Warning sound** (optional): plays on **warning** thresholds; built-in default is one file per OS (e.g. `Windows Background.wav`, `Basso.aiff`, `dialog-warning.oga`), resolved like other system media paths, then registry/`MessageBeep`/bell. Custom path in Settings.
- **Completion sound** (optional): **on/off** for the same post-queue trigger; one default per OS (e.g. `tada.wav`, `Hero.aiff`, `complete.oga`). Custom path in Settings.

### ETA, rate, and progress

- **EST. REMAINING** uses position and a **speed model**: empirical throughput from recent log updates when possible, otherwise a **recency-weighted** estimate from the prediction **window** (points). At **position 1** (at the front) it still shows an ETA by treating **one** remaining step to connecting; it is only an estimate — the log may repeat **1** for a long time.
- **Minutes per position** is labeled **Last N** under KPI **Rate** (window / dwell model; N = **Prediction window** in Settings); the full-graph average stays under **Info → Global Rate**. Dwell caps apply to the windowed KPI line. At **position 0** (queue finished), **Rate** and **Global Rate** stay fixed — derived from log timestamps only, not a clock that keeps running after you finish.
- **Progress** bar uses elapsed ÷ (elapsed + estimated remaining) when both are known; caps below **100%** while at **position 1** (at front) until the log shows past-queue-wait activity; **100%** once **position 0** is shown; empty when interrupted or ETA unknown.
- **Stale queue detection:** if no new queue lines arrive for too long relative to the expected update cadence, the run can be treated as **Interrupted**.

### Connection and status line

The status string reflects tail-of-log classification, for example:

- **Monitoring** — queue line present, in queue (`position > 1`).
- **At front** — log still shows **position 1** and the tail does not yet show a post-queue line after it (you may still wait a long time).
- **Completed** — **position 0**: a post-queue line appeared after the last queue line (connecting / loading — not only fully connected); KPI shows **0**.
- **Interrupted** — definitive disconnect / stale queue; **elapsed time freezes** but the log **keeps** being read.
- **Reconnecting…** / **Connecting…** / **Waiting for log file** / **Error** as appropriate.
- **Log silence:** no file growth for a long interval can show reconnect-style status (with guards so **At front** (1) / **Completed** (0) is not clobbered when appropriate).

### New queue after interrupt

- If a **new queue run** appears in the log while in **Interrupted**, a dialog can offer to **load** it and **re-seed** the graph and alert state for that run.

### Settings (gear)

- **Polling** — **Poll (s)** between log reads.
- **Warning Alerts** — comma-separated **thresholds**, **Warning popup** / **Warning sound** / **Warning sound file**.
- **Completion Alerts** — **on/off only** when the log shows past-queue-wait lines (no threshold list); **Completion popup**, **Completion sound**, **Completion sound file**.
- **History** — **Log every position change**: when **off**, routine queue steps are **not** written to History (alerts, completion, start/stop, and errors still are). Show or hide the panel from the main window **History** bar (still saved in config).
- **Prediction** — **Window (points)**: rolling window size for weighted rate / ETA.
- **Reset defaults** — restores built-in defaults and clears local session state tied to that flow.
- **Close** or **Escape** saves config (same debounced persistence as the rest of the app).

### Keyboard shortcuts

- **Space** — start/stop monitoring (ignored when typing in a text field).
- **Ctrl+M** — start/stop monitoring.

### Command-line interface

| Argument | Meaning |
|----------|---------|
| `--path PATH` | Initial **Logs folder** path (directory; same rules as the main window field). |
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
| `source_path` | Logs folder path string |
| `alert_thresholds` | Warning thresholds only, comma-separated (default `10, 5, 1`); not used for completion |
| `poll_sec` | Poll interval in seconds |
| `avg_window_points` | Prediction window size (points) |
| `show_log` | History pane expanded (content visible); toggled from the main window, not Settings |
| `show_status` | Info pane expanded (content visible); key name unchanged for compatibility |
| `graph_log_scale` | Graph Y axis: log vs linear |
| `popup_enabled` | Warning (threshold) popup |
| `completion_popup_enabled` | Queue completion (post-queue log signal) popup |
| `sound_enabled` | Warning (threshold) sound enabled |
| `alert_sound_path` | Warning sound file path |
| `completion_sound_enabled` | Queue completion (post-queue log signal) sound enabled |
| `completion_sound_path` | Completion sound file path |
| `show_every_change` | When true, log each queue position change to History; when false, skip routine position lines |
| `window_geometry` | Last main window size/position |
| `version` | App version string written at save time |

## Development

```bash
python -m py_compile monitor.py
```

**AI / Cursor:** This repo’s `.cursor/rules/git-commit.mdc` expects **README updates in the same commit** whenever a change affects user-facing behavior, CLI, configuration, or docs — before committing.

## License / game

This project is an independent tool for reading **your** client log. It is not affiliated with Vintage Story or its authors.
