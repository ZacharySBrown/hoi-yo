"""Build a standalone HOI-YO.exe for Windows using PyInstaller.

Usage (run from project root on a Windows machine)::

    python scripts/build_windows.py

Produces ``dist/HOI-YO.exe`` containing the complete application.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def build():
    """Run PyInstaller with the HOI-YO configuration."""

    # Ensure PyInstaller is installed
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "HOI-YO",
        "--onedir",
        # Add data files
        "--add-data", f"personas{os.sep}*;personas",
        "--add-data", f"src/dashboard/static{os.sep}*;src/dashboard/static",
        "--add-data", f"src/writer/templates{os.sep}*;src/writer/templates",
        "--add-data", f"src/cloud/templates{os.sep}*;src/cloud/templates",
        # Hidden imports that PyInstaller might miss
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        # Icon (create assets/hoi-yo.ico first)
        # "--icon", "assets/hoi-yo.ico",
        # Entry point
        str(PROJECT_ROOT / "src" / "cli.py"),
    ]

    print("Building HOI-YO.exe...")
    print(f"  Command: {' '.join(cmd[:8])}...")
    subprocess.check_call(cmd, cwd=str(PROJECT_ROOT))
    print()
    print("Build complete!")
    print(f"  Output: {PROJECT_ROOT / 'dist' / 'HOI-YO'}")
    print()
    print("To distribute:")
    print("  1. Copy the dist/HOI-YO/ directory to the target machine")
    print("  2. Pre-configure .env with ANTHROPIC_API_KEY in the same directory")
    print("  3. Create a desktop shortcut to HOI-YO.exe")


if __name__ == "__main__":
    import os
    build()
