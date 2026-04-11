# Futoshiki Project 2 (CSC14003)

This repository follows the submission organization required by the assignment.

## Directory Layout

```text
BTVN/
  source/
    main.py
    gui.py
    gui_pygame.py
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

```bash
python source/main.py --input inputs/input-01.txt --output outputs/output-01.txt --algo astar
```

Export a grounded CNF (DIMACS) for the same puzzle:

```bash
python source/main.py --input inputs/input-01.txt --export-dimacs outputs/puzzle-01.dimacs
```

## GUI (optional +10%)

Install optional dependencies (Pygame GUI):

```bash
pip install -r requirements.txt
```

### Tkinter GUI (stdlib + tk only)

```bash
python source/gui.py
```

Tkinter ships with CPython (on Linux you may need `python3-tk`). Same features as below, drawn with Tk `Canvas`.

### Pygame GUI (mockup-style)

```bash
python source/gui_pygame.py
```

Uses **Pygame** for rendering: rounded cells, white inequality symbols, dark panels, orange-highlighted algorithm row, cyan outline on **STEP-BY-STEP**, colored scrollable log, and metrics including **Solution valid** (YES / NO / In progress). File open/save still uses **Tkinter** dialogs (`withdraw()` root).

Both GUIs share the same behavior: **three columns**, load `input-*.txt`, pick an algorithm, **Solve** (calls `solve()` like the CLI), **Step-by-step** replay after a successful solve, optional save.

For the assignment **demonstration video**, start from the **command line** (show `main.py` and the input file), then optionally open a GUI to show the grid and metrics.

Supported algorithms:
- `forward`
- `backward`
- `astar`
- `backtracking`
- `bruteforce`

## Batch Benchmark

```bash
python source/main.py --batch inputs --outdir outputs
```

This command solves all `input-*.txt` files and prints runtime, nodes expanded, and memory usage.

`solved=1` only when the grid is a **verified** Latin-square solution (givens and all inequality arcs satisfied). Some sample inputs may remain `0` if no such grid exists, even when a solver’s internal propagation looked consistent.
