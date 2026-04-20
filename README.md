# VS Queue Monitor

Monitor your **Vintage Story** connect queue — live position, estimated wait time, and configurable alerts when you're close to the front.

<img width="1916" height="1072" alt="VS Queue Monitor screenshot" src="https://github.com/user-attachments/assets/648649c3-264c-4880-9e80-7a46efc4d746" />

## Quick start

### Windows — paste into Command Prompt

```bat
cmd /c "(cd /d "%USERPROFILE%\Downloads" 2>nul || cd /d "%USERPROFILE%") && curl -fsSL https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap.py | py -3 -"
```

This clones the repo, creates a virtual environment, installs dependencies, adds a Desktop shortcut, and opens the monitor.

**Python not installed yet?** Use this instead — it opens the Python installer if needed:

```bat
cmd /c "(cd /d "%USERPROFILE%\Downloads" 2>nul || cd /d "%USERPROFILE%") && curl -fsSL https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap-windows.cmd -o vs-queue-monitor-bootstrap.cmd && call vs-queue-monitor-bootstrap.cmd"
```

### macOS / Linux

```bash
(cd "$HOME/Downloads" 2>/dev/null || cd "$HOME") && curl -fsSL https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap.py | python3 -
```

### After install — launching the app

**Windows**

| Method | Steps |
|--------|-------|
| **Desktop shortcut** | Double-click **VS Queue Monitor** on the Desktop |
| **Win+R** | Press **Win+R**, type `vs-queue-monitor`, Enter |
| **Command Prompt** | `cd %USERPROFILE%\vs-queue-monitor` then `vs-queue-monitor.cmd` |
| **File Explorer** | Double-click **Run VS Queue Monitor.bat** in the install folder |

> **Win+R tip:** works system-wide once the bootstrap adds the install folder to your user PATH.

**macOS**

| Method | Steps |
|--------|-------|
| **Terminal** | `~/vs-queue-monitor/run-vs-queue-monitor.sh` |
| **Spotlight** | Press **⌘ Space**, type `run-vs-queue-monitor`, Enter (if the script is indexed) |
| **Finder** | Navigate to `~/vs-queue-monitor`, double-click `run-vs-queue-monitor.sh` |

**Linux**

| Method | Steps |
|--------|-------|
| **Terminal** | `~/vs-queue-monitor/run-vs-queue-monitor.sh` |
| **Run dialog** | Press **Alt+F2** (GNOME/KDE), type the full path to `run-vs-queue-monitor.sh` |
| **App launcher** | Add a `.desktop` entry pointing to `run-vs-queue-monitor.sh` |

If no window appears, open `http://127.0.0.1:8765/` in your browser.

### Already cloned / developing

```bash
pip install -r requirements.txt
python monitor.py
```

## Features

| | |
|---|---|
| **Live queue position** | Reads your Vintage Story client log in real time |
| **ETA & rate** | Estimates wait time from observed position changes |
| **Progress bar** | Shows how far through the queue you've moved |
| **Threshold alerts** | Popup + sound + desktop notification when position drops below a value |
| **Completion alert** | Fires when the game connects (past the queue) |
| **Graph** | Step chart of position over time; zoom, pan, export as PNG or TSV |
| **Session history** | Per-run log of position changes |
| **System tray** | Icon in notification area while running; right-click to open or quit |
| **Embedded window** | Desktop app feel via pywebview 4.x (falls back to browser if not installed) |

## Pointing at the log

In the app header, paste your **VintagestoryData** folder path or click the folder icon. Typical locations:

| OS | Default path |
|----|-------------|
| Windows | `%APPDATA%\VintagestoryData` |
| macOS | `~/Library/Application Support/VintagestoryData` |
| Linux | `~/.config/VintagestoryData` |

## System tray icon

A tray icon appears in the notification area while the service is running. Right-click for **Open VS Queue Monitor** or **Quit**.

## Options

| Flag | Effect |
|------|--------|
| `--web-browser` | Open in your default browser instead of an embedded window |
| `--path PATH` | Set the log folder on startup |
| `--no-start` | Open without auto-starting monitoring |
| `--web-port PORT` | Change the listening port (default `8765`) |

## Alerts

Default warning thresholds: position **10, 5, 1**. Edit in the **Warnings** KPI (+ or ✎). Alerts fire when your position drops *below* a threshold, once per threshold per run. Enable sound and desktop notifications in **Settings (⚙)**.

## Disclaimer

**Not affiliated with Vintage Story.** AI-assisted code — validate alerts and ETAs yourself. No warranty.

For product and UX decisions: [`docs/DESIGN.md`](docs/DESIGN.md).
