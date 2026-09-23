"""One-command PyInstaller build for the desktop dashboard.

Usage (on the target machine)::

    python build.py

Produces a single-file executable in ``dist/``.  **Build on Windows** to get
a native ``.exe`` — PyInstaller targets the OS it runs on, so this Linux VM
cannot produce a Windows executable.  See ``build_exe.bat`` for the
one-command Windows flow and ``installer.iss`` for the Inno Setup installer.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_NAME = "TradeDashboardDesktop"
ENTRY = "src/trade_dashboard_desktop/__main__.py"


def main() -> int:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller not found; installing…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", APP_NAME,
        "--paths", str(ROOT / "src"),
        # tkinter data files are collected automatically by PyInstaller's hooks
        str(ROOT / ENTRY),
    ]
    print("Running:", " ".join(cmd))
    rc = subprocess.call(cmd, cwd=ROOT)
    if rc != 0:
        print("PyInstaller build failed.")
        return rc
    exe = ROOT / "dist" / (APP_NAME + (".exe" if sys.platform == "win32" else ""))
    if exe.exists():
        print(f"Built: {exe} ({exe.stat().st_size / 1e6:.1f} MB)")
    else:
        print("Build finished but the expected output was not found in dist/.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
