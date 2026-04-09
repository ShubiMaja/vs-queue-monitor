# Vintage Story Queue Monitor

Desktop app (Python + Tkinter) that tails the **Vintage Story** client log, tracks **connect queue position**, estimates **wait time**, and raises **alerts** when you cross configurable thresholds (popup + optional sound on Windows).

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
   cd /path/to/vs-q-monitor
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
   cd /path/to/vs-q-monitor
   python3 monitor.py
   ```

### Linux (Fedora / RHEL-like)

```bash
sudo dnf install python3 python3-tkinter
cd /path/to/vs-q-monitor
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

Exact Vintage Story data locations depend on your install; use the **File or directory** field in the app if unsure.

## Log file

The game writes queue lines similar to:

- `Client is in connect queue at position: N`
- `Your position in the queue is: N`

The default path hint in the UI targets Windows (`%APPDATA%/VintagestoryData/...`). On macOS or Linux, browse to your Vintage Story data folder or paste the full path to `client-main.log`. If you pass a **directory**, the app searches for `client-main.log` (and a few fallbacks) under common layouts.

## Features (short)

| Area | Behavior |
|------|----------|
| **Status bar** | Position, status, elapsed, remaining ETA, progress (elapsed vs ETA when known) |
| **Graph** | Recent queue position over time; optional log-scaled Y axis |
| **Alerts** | Comma-separated thresholds; **default** `10, 5, 3, 2, 1`. One alert per threshold per downward crossing per queue run |
| **Reconnect / interrupt** | Distinguishes grace-period TCP errors vs final teardown; optional log-silence detection; **Interrupted** freezes elapsed but **keeps tailing** the log |
| **New queue** | After an interrupt, if a **new queue run** appears in the log, a dialog offers to **re-seed** the graph for that run |
| **Config** | Settings and window geometry persist to JSON (see below) |

## Configuration file

Saved automatically (debounced) when you change options:

| OS | Path |
|----|------|
| Windows | `%APPDATA%\vs-q-monitor\config.json` |
| Linux/macOS | `$XDG_CONFIG_HOME/vs-q-monitor/config.json` or `~/.config/vs-q-monitor/config.json` |

Typical keys: `source_path`, `alert_thresholds` (default `10, 5, 3, 2, 1`), `poll_sec`, `avg_window_points`, `show_log`, `graph_log_scale`, `popup_enabled`, `sound_enabled`, `show_every_change`, `window_geometry`.

## Development

```bash
python -m py_compile monitor.py
```

## License / game

This project is an independent tool for reading **your** client log. It is not affiliated with Vintage Story or its authors.
