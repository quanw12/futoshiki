# Futoshiki Project 2 (CSC14003)

This repository follows the submission organization required by the assignment.

## Directory Layout

```text
BTVN/
  source/
    main.py
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

```bash
python source/main.py --input inputs/input-01.txt --output outputs/output-01.txt --algo astar
```

Export a grounded CNF (DIMACS) for the same puzzle:

```bash
python source/main.py --input inputs/input-01.txt --export-dimacs outputs/puzzle-01.dimacs
```

## GUI (optional)

```bash
python source/gui.py
```

Open an `input-*.txt` file, choose an algorithm, then **Solve**. You can save the formatted solution to a text file.

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
