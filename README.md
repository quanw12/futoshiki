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

The legacy Qt/Tk UIs were removed; the JS UI is the only UI in this repo.
