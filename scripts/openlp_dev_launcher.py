"""Native Windows launcher for OpenLP dev copy.

This is intended to be frozen with PyInstaller (`--windowed`) so the launcher
itself has no console window and can be pinned with the OpenLP icon.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _get_repo_root() -> Path:
    # When frozen, the exe is expected in <repo>/dist/OpenLPDev.exe
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent.parent
    return Path(__file__).resolve().parent.parent


def main() -> int:
    repo_root = _get_repo_root()
    pythonw = repo_root / '.venv' / 'Scripts' / 'pythonw.exe'
    run_script = repo_root / 'run_openlp.py'

    if not pythonw.exists() or not run_script.exists():
        return 1

    subprocess.Popen(
        [str(pythonw), str(run_script), '-p'],
        cwd=str(repo_root),
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
