# Futoshiki Project 2 (CSC14003)

This repository follows the submission organization required by the assignment.

## Directory Layout

```text
BTVN/
  source/
    algorithm/
      astar.py
      backtracking.py
      backward.py
      bruteforce.py
      forward.py
    benchmark_compare.py
    ground_kb.py
    validate_outputs.py
    ui/
      src/
      electron/
      package.json
    futoshiki_core.py
    solvers.py
    api_server.py
  inputs/
    input-01.txt ... input-10.txt
  outputs/
    (generated output-01.txt ... output-10.txt)
  FOL_AXIOMS.md
  Report.tex
  requirements.txt
```

## Run

### Pure benchmark workflow (comparison-first)

Use this flow to compare algorithms fairly (pure runs, no hidden fallback in orchestration):

```bash
python source/benchmark_compare.py
python source/validate_outputs.py
```

Benchmark behavior:
- Uses `inputs/input-01..10.txt` (sizes `4,4,5,5,6,6,7,7,9,9`)
- Runs `forward`, `backward`, `astar`, `backtracking`, `bruteforce` independently
- Writes per-algorithm outputs to `outputs/<algo>-output-XX.txt`
- Writes canonical required files to `outputs/output-XX.txt` from pure backtracking results
- Writes comparison metrics to `outputs/benchmark-summary.json`

### Ground KB + CNF generation (DIMACS)

Generate grounded CNF from any input file:

```bash
python source/ground_kb.py inputs/input-01.txt outputs/puzzle-01.dimacs
python source/ground_kb.py inputs/input-01.txt outputs/tmp-01.cnf
```

This provides:
- grounded `Val(i,j,v)` propositional atoms
- CNF clauses for domain/uniqueness/given/inequality constraints
- DIMACS output for SAT/resolution verification

### New JS Liquid UI (recommended)

This mode keeps **all solving algorithms in Python**, but moves the app UI to React for richer visuals and smoother motion.

1) Start Python API backend:

```bash
pip install -r requirements.txt
uvicorn source.api_server:app --reload --port 8000
```

2) Start React UI:

```bash
cd source/ui
npm install
npm run dev
```

Open `http://localhost:5173`.

The web UI calls Python endpoints (`/api/solve`, `/api/puzzle/parse`, `/api/puzzle/validate`, `/api/export`) so Futoshiki rules and solver behavior remain unchanged.
It also supports loading sample testcases directly from the repo `inputs/` folder and running trace replay from solver events.

### Desktop wrapper (Electron)

Run the web UI as a desktop app (native-like window) while solver logic still runs in Python:

```bash
cd source/ui
npm install
npm run desktop
```

`npm run desktop` will:
- build the React UI
- launch an Electron window
- auto-start Python backend (`uvicorn source.api_server:app`) from repo root

Supported algorithms:
- `forward`
- `backward`
- `astar`
- `backtracking`
- `bruteforce`

Notes on modes:
- Official comparison mode is pure (no cross-algorithm fallback in dispatcher).
- If you want hybrid behavior for experimentation, keep it as a separate explicit path, not the benchmark default.

The legacy Qt/Tk UIs were removed; the JS UI is the only UI in this repo.
