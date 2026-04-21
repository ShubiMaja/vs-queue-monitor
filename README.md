# VS Queue Monitor

Monitor your **Vintage Story** connect queue — live position, estimated wait time, and configurable alerts when you're close to the front.

<img width="1181" height="924" alt="image" src="https://github.com/user-attachments/assets/a0d34f86-096b-4f08-a470-d44904dcda92" />

## Quick start

### Windows — paste into Command Prompt

```bat
cmd /c "(cd /d "%USERPROFILE%\Downloads" 2>nul || cd /d "%USERPROFILE%") && curl -fsSL https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap.py | py -3 -"
```

This clones the repo, installs dependencies, and opens the monitor. After install, relaunch any time with **Win+R → `vs-queue-monitor`** or the Desktop shortcut.

**Python not installed yet?** Use this instead — it opens the Python installer if needed:

```bat
cmd /c "(cd /d "%USERPROFILE%\Downloads" 2>nul || cd /d "%USERPROFILE%") && curl -fsSL https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap-windows.cmd -o vs-queue-monitor-bootstrap.cmd && call vs-queue-monitor-bootstrap.cmd"
```

### macOS / Linux

```bash
(cd "$HOME/Downloads" 2>/dev/null || cd "$HOME") && curl -fsSL https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap.py | python3 -
```

After install, relaunch any time with `~/vs-queue-monitor/run-vs-queue-monitor.sh` or **⌘ Space → `run-vs-queue-monitor`** on macOS.

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

## Remote access via ngrok

You can expose a local port to the internet securely with [ngrok](https://dashboard.ngrok.com/get-started/setup/windows).

The following command will expose the default port that the app runs on and protect it with Google Authentication 

`ngrok http 8765 --oauth google --oauth-allow-email myname@gmail.com`

### Expected Output

```
Update                        update available (version 3.38.0, Ctrl-U to update)
Version                       3.37.3
Region                        Europe (eu)
Latency                       63ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://1eaa-80-230-11-63.ngrok-free.app -> http://localhost:8765  
```

By default, the dns it forwards to is different each time. So for example according to the Forwarding rule, above, the UI would be available at:  https://1eaa-80-230-11-63.ngrok-free.app

## Remote access via SSH tunnel

If Vintage Story is running on a machine you access over SSH (e.g. a gaming PC, home server, or cloud VM), you can still view the monitor in your local browser:

**1. Start the server on the remote machine** (no window needed):

```bash
python monitor.py --web-browser --path /path/to/VintagestoryData
```

**2. Open an SSH tunnel from your laptop:**

```bash
ssh -L 8765:localhost:8765 user@remote-host
```

**3. Open `http://localhost:8765` in your local browser.**

The tunnel forwards your laptop's port 8765 to the server's loopback — nothing is exposed to the internet. Replace `8765` with `--web-port` value if you changed it.

> **Tip:** add `-N` to the SSH command (`ssh -N -L ...`) to open just the tunnel without a shell.

## Disclaimer

**Not affiliated with Vintage Story.** AI-assisted code — validate alerts and ETAs yourself. No warranty.

For product and UX decisions: [`docs/DESIGN.md`](docs/DESIGN.md).
