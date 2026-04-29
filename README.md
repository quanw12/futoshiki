# Futoshiki Puzzle Solver — Project 2 (CSC14003)

> **Introduction to Artificial Intelligence**  
> Faculty of Information Technology, University of Science, VNU-HCM

Futoshiki (不等式 — "inequality" in Japanese) is a logic-based number placement puzzle played on
an **N × N** grid. The solver must fill every empty cell with a value from **1** to **N** such that:

1. Each row contains all values **1 … N** exactly once (**Latin square**).
2. Each column contains all values **1 … N** exactly once.
3. All inequality constraints (`<`, `>`) between adjacent cells are satisfied.

This project formalises the puzzle in **First-Order Logic (FOL)**, implements five solving
algorithms from scratch, and provides a modern GUI for interactive exploration.

---

## Directory Layout

```
Futoshiki-Puzzles/
├── source/                     # All solver & UI source code
│   ├── futoshiki_core.py       #   Core types, I/O, CSP helpers (AC-3, MRV, …)
│   ├── ground_kb.py            #   Automatic CNF / DIMACS generation from FOL
│   ├── validate_outputs.py     #   Batch validator for output-01..10
│   ├── api_server.py           #   FastAPI backend for the web/desktop UI
│   ├── main.py                 #   Electron desktop launcher
│   ├── algorithm/              #   Algorithm implementations
│   │   ├── __init__.py         #     Unified solve() dispatcher + post-check
│   │   ├── forward.py          #     Forward chaining (AC-3 + hidden singles + naked pairs + probing)
│   │   ├── backward.py         #     Backward chaining / SLD resolution (Prolog-style)
│   │   ├── astar.py            #     A* search with admissible heuristic + MRV branching
│   │   ├── backtracking.py     #     Backtracking + AC-3 (MRV variable ordering)
│   │   └── bruteforce.py       #     Brute-force DFS (no AC-3, no MRV)
│   ├── assets/                 #   Arrow images for inequality rendering
│   └── ui/                     #   React + Vite + Electron frontend
│       ├── src/                #     React components, styles, utilities
│       ├── electron/           #     Electron main process (main.cjs)
│       ├── package.json
│       └── vite.config.js
├── inputs/                     # 10 test case files (4×4 … 9×9)
│   ├── input-01.txt
│   └── …
├── outputs/                    # Solved grids (output-01.txt … output-10.txt)
│   ├── output-01.txt
│   └── …
├── requirements.txt            # Python dependencies
└── README.md                   # ← You are here
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| **Python** | 3.10 or later |
| **Node.js** | 18+ (for the desktop GUI) |
| **pip** | bundled with Python |

Install Python dependencies:

```bash
pip install -r requirements.txt
```

For the desktop GUI, also install Node packages:

```bash
cd source/ui
npm install
```

---

## How to Run

### 1. Ground KB — CNF / DIMACS Generation

Generate a grounded CNF from any input file (FOL → propositions → DIMACS):

```bash
cd source
python ground_kb.py ../inputs/input-01.txt ../outputs/puzzle-01.dimacs
```

### 2. Desktop App (Electron)

Wraps the React UI in a native window and **auto-starts the Python API backend**.
All solving logic stays in Python; the GUI calls the API endpoints internally.

```bash
cd source/ui
npm install
npm run desktop
```

The app will:
- Build the React frontend
- Launch Electron with a native window
- Auto-start the Python backend (`uvicorn source.api_server:app`)

Supported algorithms: **Forward Chaining**, **Backward Chaining (SLD)**, **A\* Search**,
**Backtracking**, **Brute Force**.

---

## Algorithms

| # | Algorithm | Module | Description |
|---|-----------|--------|-------------|
| 1 | **Forward Chaining** | `forward.py` | Iterative propagation: AC-3 → singleton elimination → hidden singles → naked pairs → singleton probing. Falls back to backtracking if propagation alone reaches a fixpoint without full assignment. |
| 2 | **Backward Chaining** | `backward.py` | SLD-style Prolog interpreter: selects the cell with fewest candidates (MRV), tries each value, recurses. Equivalent to querying `Val(i, j, ?)` for every cell. |
| 3 | **A\* Search** | `astar.py` | Best-first search over partial assignments. Uses an admissible heuristic `h(s) = 0 if goal, 1 otherwise` combined with AC-3 domain reduction and MRV tie-breaking. |
| 4 | **Backtracking + AC-3** | `backtracking.py` | Classical backtracking with MRV variable ordering and AC-3 domain propagation after each assignment. |
| 5 | **Brute Force** | `bruteforce.py` | Pure DFS without constraint propagation or intelligent variable ordering. Baseline for performance comparison. |

---

## Input Format

Each input file follows this structure:

```
N
# Grid: N rows × N columns (0 = empty, 1..N = pre-filled)
v1, v2, ..., vN
...
# Horizontal constraints: N rows × (N-1) columns
# 0 = none, 1 = left < right, -1 = left > right
h1, h2, ..., h(N-1)
...
# Vertical constraints: (N-1) rows × N columns
# 0 = none, 1 = top < bottom, -1 = top > bottom
v1, v2, ..., vN
...
```

**Example** (`input-01.txt`, 4 × 4):

```
4
2,0,0,1
0,2,0,3
0,3,1,0
3,1,2,0
0,0,-1
0,0,-1
0,0,0
0,0,0
0,0,0,0
0,1,0,-1
0,0,0,0
```

## Output Format

The solved grid with inequality symbols (`<`, `>`, `^`, `v`) for readability:

```
2   4   3 > 1

1   2   4 > 3
    ^       v
4   3   1   2

3   1   2   4
```

Where `<` / `>` denotes horizontal constraints and `^` / `v` denotes vertical
constraints (top < bottom = `^`, top > bottom = `v`).

---

## Test Cases

| File | Grid Size | Difficulty |
|------|-----------|------------|
| `input-01` | 4 × 4 | Easy |
| `input-02` | 4 × 4 | Easy |
| `input-03` | 5 × 5 | Medium |
| `input-04` | 5 × 5 | Medium |
| `input-05` | 6 × 6 | Medium |
| `input-06` | 6 × 6 | Medium |
| `input-07` | 7 × 7 | Hard |
| `input-08` | 7 × 7 | Hard |
| `input-09` | 9 × 9 | Hard |
| `input-10` | 9 × 9 | Hard |

---

## License

This project is an academic assignment for **CSC14003 — Introduction to Artificial Intelligence**.
