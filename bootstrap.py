#!/usr/bin/env python3
"""
One-file launcher: find or clone the repo, create .venv, install deps, run monitor.py.

Usage (after download):
  python bootstrap.py              # default: embedded web UI
  python bootstrap.py --gui        # classic Tk window
  python3 bootstrap.py --tui

Pipe (no saved file; clones to ~/vs-queue-monitor by default):
  curl -fsSL https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap.py | python3 -

Override install location:
  set VS_QUEUE_MONITOR_HOME=C:\\path\\to\\clone
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

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
    _eprint("→", " ".join(cmd))
    r = subprocess.run(cmd, cwd=cwd, env=env)
    if r.returncode != 0:
        raise SystemExit(r.returncode)


def _ensure_git_repo(root: Path) -> None:
    """Ensure ``root`` is a git checkout of the app (clone or pull)."""
    git_dir = root / ".git"
    if git_dir.is_dir():
        _eprint("Updating existing clone…")
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

    _eprint(f"Cloning {REPO_URL} (branch {REPO_BRANCH})…")
    try:
        _run(
            ["git", "clone", "--depth", "1", "-b", REPO_BRANCH, REPO_URL, str(root)],
            cwd=parent,
        )
    except SystemExit:
        _eprint("Retrying clone without branch pin…")
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
    _eprint("Installing dependencies (pip)…")
    _run([str(py), "-m", "pip", "install", "--upgrade", "pip"], cwd=root)
    _run([str(py), "-m", "pip", "install", "-r", str(req)], cwd=root)


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

    monitor = root / "monitor.py"
    args = [str(py), str(monitor), *sys.argv[1:]]
    _eprint("Starting VS Queue Monitor…")
    env = os.environ.copy()
    # So subprocess inherits sane cwd for relative paths
    os.chdir(root)
    r = subprocess.run(args, cwd=root, env=env)
    raise SystemExit(r.returncode)


if __name__ == "__main__":
    main()
