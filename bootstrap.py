#!/usr/bin/env python3
"""
One-file launcher: find or clone the repo, create .venv, install deps, optional run.

Usage (after download):
  python bootstrap.py              # embedded web UI (local HTTP + webview or browser)

On Windows, after pip install, creates a Desktop shortcut to ``vs-queue-monitor.cmd`` unless
``VS_QUEUE_MONITOR_NO_DESKTOP_SHORTCUT`` is set. If stdin is a TTY (e.g. you ran
``python bootstrap.py`` from a terminal), asks ``Start VS Queue Monitor now? [Y/n]``.
Piped installs (``curl ... | python -``) start the app without prompting. Set
``VS_QUEUE_MONITOR_SKIP_RUN=1`` to exit after install without starting.

After a full clone, Windows users can double-click ``Run VS Queue Monitor.bat``
or use Win+R with ``vs-queue-monitor.cmd`` (see README). If Python is not installed, those
launchers warn you, open the official Python download page, and exit.

Windows (no Python on PATH yet): use ``bootstrap-windows.cmd`` from the repo or
the README one-liner; it checks for ``py`` / ``python`` before piping this script.

Pipe (no saved file; clones to ~/vs-queue-monitor by default). Prefer the README
one-liners: they use **Downloads** when that folder already exists (never created
by us), otherwise your profile/home, before ``curl``. ``bootstrap-windows.cmd``
does the same before fetching.

  curl -fsSL https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap.py | python3 -

Override install location:
  set VS_QUEUE_MONITOR_HOME=C:\\path\\to\\clone
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Display name for Windows desktop shortcut (keep in sync with vs_queue_monitor.APP_DISPLAY_NAME).
_APP_SHORTCUT_STEM = "VS Queue Monitor"

# Canonical upstream (forks: set VS_QUEUE_MONITOR_REPO to a git URL).
REPO_URL = os.environ.get("VS_QUEUE_MONITOR_REPO", "https://github.com/ShubiMaja/vs-queue-monitor.git")
REPO_BRANCH = os.environ.get("VS_QUEUE_MONITOR_BRANCH", "main")


def _eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def _bootstrap_path() -> Path | None:
    try:
        return Path(__file__).resolve()
    except NameError:
        return None


def _default_home() -> Path:
    raw = os.environ.get("VS_QUEUE_MONITOR_HOME", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.home() / "vs-queue-monitor").resolve()


def _is_project_root(p: Path) -> bool:
    return (p / "monitor.py").is_file() and (p / "vs_queue_monitor").is_dir()


def _find_project_root() -> Path | None:
    bp = _bootstrap_path()
    if bp is not None:
        parent = bp.parent
        if _is_project_root(parent):
            return parent
    cwd = Path.cwd().resolve()
    if _is_project_root(cwd):
        return cwd
    home = _default_home()
    if _is_project_root(home):
        return home
    return None


def _venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> None:
    _eprint("->", " ".join(cmd))
    r = subprocess.run(cmd, cwd=cwd, env=env)
    if r.returncode != 0:
        raise SystemExit(r.returncode)


def _ensure_git_repo(root: Path) -> None:
    """Ensure ``root`` is a git checkout of the app (clone or pull)."""
    git_dir = root / ".git"
    if git_dir.is_dir():
        _eprint("Updating existing clone...")
        try:
            _run(["git", "-C", str(root), "pull", "--ff-only"], cwd=root)
        except SystemExit:
            _eprint("(git pull failed; continuing with existing files)")
        return

    parent = root.parent
    parent.mkdir(parents=True, exist_ok=True)

    if root.exists():
        try:
            if any(root.iterdir()):
                _eprint(f"Directory exists and is not a git repo: {root}")
                raise SystemExit(1)
        except OSError:
            raise SystemExit(1)

    _eprint(f"Cloning {REPO_URL} (branch {REPO_BRANCH})...")
    try:
        _run(
            ["git", "clone", "--depth", "1", "-b", REPO_BRANCH, REPO_URL, str(root)],
            cwd=parent,
        )
    except SystemExit:
        _eprint("Retrying clone without branch pin...")
        if root.exists():
            import shutil

            shutil.rmtree(root, ignore_errors=True)
        _run(["git", "clone", "--depth", "1", REPO_URL, str(root)], cwd=parent)


def _ensure_venv(root: Path) -> Path:
    venv = root / ".venv"
    py = _venv_python(venv)
    if not py.is_file():
        _eprint(f"Creating virtualenv: {venv}")
        _run([sys.executable, "-m", "venv", str(venv)], cwd=root)
    if not py.is_file():
        _eprint("venv python missing after venv creation")
        raise SystemExit(1)
    return py


def _pip_install(py: Path, root: Path) -> None:
    req = root / "requirements.txt"
    if not req.is_file():
        _eprint(f"Missing requirements.txt in {root}")
        raise SystemExit(1)
    _eprint("Installing dependencies (pip)...")
    _run([str(py), "-m", "pip", "install", "--upgrade", "pip"], cwd=root)
    _run([str(py), "-m", "pip", "install", "-r", str(req)], cwd=root)


def _windows_desktop_dir() -> Path | None:
    """Resolve the user Desktop folder (handles OneDrive / localized profiles)."""
    try:
        r = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "[Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if r.returncode == 0 and r.stdout:
            p = Path(r.stdout.strip())
            if p.is_dir():
                return p
    except OSError:
        pass
    fallback = Path.home() / "Desktop"
    return fallback if fallback.is_dir() else None


def _ps_single_quoted(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def _create_windows_desktop_shortcut(root: Path) -> None:
    """Create a .lnk on the Desktop pointing at vs-queue-monitor.cmd (or legacy vsqm.cmd / .bat).

    Skips silently when the shortcut already exists. When it does not exist and stdin is a TTY,
    asks the user first. Non-interactive runs (piped bootstrap) create it automatically.
    """
    if sys.platform != "win32":
        return
    if os.environ.get("VS_QUEUE_MONITOR_NO_DESKTOP_SHORTCUT", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        _eprint("Skipping desktop shortcut (VS_QUEUE_MONITOR_NO_DESKTOP_SHORTCUT is set).")
        return
    launcher = root / "vs-queue-monitor.cmd"
    if not launcher.is_file():
        launcher = root / "vsqm.cmd"
    if not launcher.is_file():
        launcher = root / "Run VS Queue Monitor.bat"
    if not launcher.is_file():
        _eprint("(No vs-queue-monitor.cmd / Run VS Queue Monitor.bat - skipping desktop shortcut.)")
        return
    desktop = _windows_desktop_dir()
    if desktop is None:
        _eprint("(Could not resolve Desktop - skipping shortcut.)")
        return
    lnk = desktop / f"{_APP_SHORTCUT_STEM}.lnk"

    if lnk.exists():
        return  # already there - nothing to do

    if sys.stdin.isatty():
        try:
            answer = input("Add a Desktop shortcut for VS Queue Monitor? [Y/n] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            _eprint("")
            return
        if answer in ("n", "no"):
            return

    ps = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut({_ps_single_quoted(str(lnk))}); "
        f"$s.TargetPath = {_ps_single_quoted(str(launcher.resolve()))}; "
        f"$s.WorkingDirectory = {_ps_single_quoted(str(root.resolve()))}; "
        f"$s.Description = {_ps_single_quoted(_APP_SHORTCUT_STEM + ' - Vintage Story queue monitor')}; "
        "$s.Save()"
    )
    r = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        cwd=root,
        check=False,
    )
    if r.returncode == 0:
        _eprint(f"Desktop shortcut created: {lnk}")
    else:
        _eprint("(Could not create desktop shortcut; you can run vs-queue-monitor.cmd from the install folder.)")


def _setup_push_notifications(py: Path, root: Path) -> None:
    """Trigger VAPID key auto-generation so push notifications work from the first start."""
    _eprint("Setting up push notifications...")
    r = subprocess.run(
        [
            str(py),
            "-c",
            (
                "import sys; sys.path.insert(0, r'" + str(root) + "'); "
                "from vs_queue_monitor.web.push import _auto_setup_vapid, push_configured; "
                "_auto_setup_vapid(); "
                "print('  Push notifications ready.' if push_configured() "
                "else '  Push notifications unavailable (pywebpush not installed).', file=sys.stderr)"
            ),
        ],
        cwd=root,
        check=False,
    )
    if r.returncode != 0:
        _eprint("  (Push notification setup skipped.)")


def _should_run_monitor_after_install() -> bool:
    """Respect VS_QUEUE_MONITOR_SKIP_RUN; if stdin is a TTY, ask to start now."""
    sk = os.environ.get("VS_QUEUE_MONITOR_SKIP_RUN", "").strip().lower()
    if sk in ("1", "true", "yes", "y"):
        return False
    if not sys.stdin.isatty():
        return True
    try:
        reply = input("Start VS Queue Monitor now? [Y/n]: ")
    except EOFError:
        return True
    r = (reply or "").strip().lower()
    return r in ("", "y", "yes")


def _print_launch_hint(root: Path) -> None:
    """Tell users which file to double-click / run after install."""
    _eprint("")
    _eprint("-" * 58)
    _eprint("Run this app later from the project folder:")
    if sys.platform == "win32":
        bat = root / "Run VS Queue Monitor.bat"
        if bat.is_file():
            _eprint(f"  * Double-click: {bat.name}")
        else:
            _eprint("  * Double-click: Run VS Queue Monitor.bat  (included in a full git checkout)")
        if (root / "vs-queue-monitor.cmd").is_file():
            _eprint("  * Win+R: add this folder to your user PATH, then run  vs-queue-monitor   (see README)")
        _eprint(rf"  * Or terminal: {root / '.venv' / 'Scripts' / 'python.exe'} monitor.py")
    else:
        sh = root / "run-vs-queue-monitor.sh"
        if sh.is_file():
            _eprint(f"  * Terminal: ./{sh.name}   (once: chmod +x {sh.name})")
        _eprint("  * Or: python3 monitor.py")
    _eprint("-" * 58)
    _eprint("")


def main() -> None:
    root = _find_project_root()
    if root is None:
        root = _default_home()
        _eprint(f"No monitor.py next to this script or in cwd; installing under: {root}")
        _ensure_git_repo(root)
    if not _is_project_root(root):
        _eprint(f"Invalid project root after setup: {root}")
        raise SystemExit(1)

    py = _ensure_venv(root)
    _pip_install(py, root)
    _setup_push_notifications(py, root)
    _create_windows_desktop_shortcut(root)
    _print_launch_hint(root)

    if not _should_run_monitor_after_install():
        _eprint("Not starting the app (you can use the Desktop shortcut or run vs-queue-monitor.cmd later).")
        raise SystemExit(0)

    monitor = root / "monitor.py"
    args = [str(py), str(monitor), *sys.argv[1:]]
    _eprint("Starting VS Queue Monitor...")
    env = os.environ.copy()
    # So subprocess inherits sane cwd for relative paths
    os.chdir(root)
    r = subprocess.run(args, cwd=root, env=env)
    raise SystemExit(r.returncode)


if __name__ == "__main__":
    main()
