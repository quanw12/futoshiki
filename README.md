# Futoshiki Project 2 (CSC14003)

This repository follows the submission organization required by the assignment.

## Directory Layout

```text
BTVN/
  source/
    main.py
    gui_qt.py
    gui_customtk.py
    gui.py
    futoshiki_core.py
    solvers.py
    ground_kb.py
  inputs/
    input-01.txt ... input-10.txt
  outputs/
    (generated output-01.txt ... output-10.txt)
  FOL_AXIOMS.md
  Report.tex
  requirements.txt
```

## Run

## GUI (optional +10%)

Install dependencies:

```bash
pip install -r requirements.txt
```

### Tkinter GUI (stdlib + tk only)

```bash
python source/gui.py
```

Tkinter ships with CPython (on Linux you may need `python3-tk`). Same features as below, drawn with Tk `Canvas`.

### PySide6 GUI (default)

```bash
python source/main.py
```

Uses **PySide6** with custom-painted board and liquid-glass inspired visual style, preserving solver logic and inequality/arrow rules.

Legacy UIs still exist in `source/gui_customtk.py` and `source/gui.py` if needed.

Supported algorithms:
- `forward`
- `backward`
- `astar`
- `backtracking`
- `bruteforce`

CLI mode was removed; `source/main.py` is now the UI entrypoint.
