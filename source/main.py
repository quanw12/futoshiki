"""Launcher for the Futoshiki desktop UI (React + Electron)."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def main() -> None:
    ui_dir = Path(__file__).resolve().parent / "ui"
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("npm not found in PATH. Please install Node.js.")
    result = subprocess.run([npm, "run", "desktop"], cwd=str(ui_dir), check=False)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
