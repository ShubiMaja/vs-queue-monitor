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

### Already cloned / developing

```bash
pip install -r requirements.txt
python monitor.py
```

If no window appears, open `http://127.0.0.1:8765/` in your browser.

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
