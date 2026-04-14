"""Main entrypoint for the PySide6 UI."""
from __future__ import annotations

import os
import sys

# Allow `python source/main.py` from repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui_qt import main  # noqa: E402


if __name__ == "__main__":
    main()
