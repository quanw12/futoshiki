"""FastAPI backend for JS UI while keeping solver logic in Python."""
from __future__ import annotations

from dataclasses import asdict
import multiprocessing
import os
import sys
from pathlib import Path
from typing import List, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure solver modules in `source/` are importable when launched as
# `uvicorn source.api_server:app` from repo root.
SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

from futoshiki_core import Puzzle, is_valid_solution
from solvers import solve

AlgoName = Literal["forward", "backward", "astar", "backtracking", "bruteforce"]
SOLVE_TIMEOUT_SEC = 300


class PuzzlePayload(BaseModel):
    n: int = Field(ge=2, le=12)
    grid: List[List[int]]
    hcons: List[List[int]]
    vcons: List[List[int]]


class ParseInputRequest(BaseModel):
    content: str


class SolveRequest(BaseModel):
    algo: AlgoName
    puzzle: PuzzlePayload


class ValidateRequest(BaseModel):
    puzzle: PuzzlePayload
    grid: List[List[int]]


class ExportRequest(BaseModel):
    puzzle: PuzzlePayload
    solved: List[List[int]]


def _parse_csv_line(line: str) -> List[int]:
    return [int(x.strip()) for x in line.split(",")]


def _parse_puzzle_text(content: str) -> Puzzle:
    raw = [ln.strip() for ln in content.splitlines()]
    lines = [ln for ln in raw if ln and not ln.startswith("#")]
    if not lines:
        raise ValueError("Empty puzzle input.")
    n = int(lines[0])
    idx = 1
    if len(lines) < 1 + n + n + (n - 1):
        raise ValueError("Input does not contain enough rows for grid/constraints.")
    grid = [_parse_csv_line(lines[idx + r]) for r in range(n)]
    idx += n
    hcons = [_parse_csv_line(lines[idx + r]) for r in range(n)]
    idx += n
    vcons = [_parse_csv_line(lines[idx + r]) for r in range(n - 1)]
    return Puzzle(n, grid, hcons, vcons)


def _validate_shape(p: PuzzlePayload) -> None:
    n = p.n
    if len(p.grid) != n or any(len(row) != n for row in p.grid):
        raise ValueError("grid shape must be n x n")
    if len(p.hcons) != n or any(len(row) != n - 1 for row in p.hcons):
        raise ValueError("hcons shape must be n x (n-1)")
    if len(p.vcons) != n - 1 or any(len(row) != n for row in p.vcons):
        raise ValueError("vcons shape must be (n-1) x n")


def _to_puzzle(p: PuzzlePayload) -> Puzzle:
    _validate_shape(p)
    return Puzzle(p.n, [row[:] for row in p.grid], [row[:] for row in p.hcons], [row[:] for row in p.vcons])


def _solve_worker(algo: str, puzzle_payload: dict, out_queue: multiprocessing.Queue) -> None:
    """Run solve in isolated process so we can enforce hard timeout."""
    try:
        p = Puzzle(
            puzzle_payload["n"],
            [row[:] for row in puzzle_payload["grid"]],
            [row[:] for row in puzzle_payload["hcons"]],
            [row[:] for row in puzzle_payload["vcons"]],
        )
        res = solve(p, algo)
        out_queue.put(
            {
                "ok": True,
                "result": {
                    "solved_grid": res.solved_grid,
                    "runtime_sec": res.runtime_sec,
                    "nodes_expanded": res.nodes_expanded,
                    "memory_kb": res.memory_kb,
                    "contradiction": res.contradiction,
                    "messages": res.messages,
                    "trace": res.trace,
                },
            }
        )
    except Exception as exc:  # noqa: BLE001
        out_queue.put({"ok": False, "error": str(exc)})


def _solve_with_timeout(p: Puzzle, algo: str) -> dict:
    queue: multiprocessing.Queue = multiprocessing.Queue(maxsize=1)
    proc = multiprocessing.Process(target=_solve_worker, args=(algo, asdict(p), queue), daemon=True)
    proc.start()
    proc.join(timeout=SOLVE_TIMEOUT_SEC)

    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=2)
        raise TimeoutError(f"Solver exceeded {SOLVE_TIMEOUT_SEC}s timeout.")

    if proc.exitcode not in (0, None) and queue.empty():
        raise RuntimeError("Solver process exited unexpectedly.")

    if queue.empty():
        raise RuntimeError("Solver returned no result.")

    payload = queue.get()
    if not payload.get("ok"):
        raise RuntimeError(payload.get("error", "Solver failed with unknown error."))
    return payload["result"]


def _render_solution_text(p: Puzzle, solved: List[List[int]]) -> str:
    lines: List[str] = []
    for i in range(p.n):
        row: List[str] = []
        for j in range(p.n):
            row.append(str(solved[i][j]))
            if j < p.n - 1:
                c = p.hcons[i][j]
                row.append("<" if c == 1 else ">" if c == -1 else " ")
        lines.append(" ".join(row))
        if i < p.n - 1:
            vr: List[str] = []
            for j in range(p.n):
                c = p.vcons[i][j]
                vr.append("v" if c == 1 else "^" if c == -1 else " ")
                if j < p.n - 1:
                    vr.append(" ")
            lines.append(" ".join(vr))
    return "\n".join(lines) + "\n"


app = FastAPI(title="Futoshiki API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


def _inputs_dir() -> Path:
    return Path(SOURCE_DIR).parent / "inputs"


@app.get("/api/inputs")
def list_inputs() -> dict:
    root = _inputs_dir()
    if not root.exists():
        return {"files": []}
    files = sorted(p.name for p in root.glob("*.txt") if p.is_file())
    return {"files": files}


@app.get("/api/inputs/{filename}")
def read_input_file(filename: str) -> dict:
    # Prevent path traversal; only allow file names within inputs folder.
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid file name.")
    path = _inputs_dir() / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Input file not found.")
    content = path.read_text(encoding="utf-8")
    return {"name": filename, "content": content}


@app.post("/api/puzzle/parse")
def parse_puzzle(req: ParseInputRequest) -> dict:
    try:
        p = _parse_puzzle_text(req.content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"puzzle": asdict(p)}


@app.post("/api/puzzle/validate")
def validate_solution(req: ValidateRequest) -> dict:
    try:
        p = _to_puzzle(req.puzzle)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ok = is_valid_solution(p, req.grid)
    return {"valid": ok}


@app.post("/api/solve")
def solve_puzzle(req: SolveRequest) -> dict:
    try:
        p = _to_puzzle(req.puzzle)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        return _solve_with_timeout(p, req.algo)
    except TimeoutError as exc:
        raise HTTPException(
            status_code=408,
            detail=f"{exc} Please switch algorithm or use an easier testcase.",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/export")
def export_solution(req: ExportRequest) -> dict:
    try:
        p = _to_puzzle(req.puzzle)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not is_valid_solution(p, req.solved):
        raise HTTPException(status_code=400, detail="Grid is not a valid Futoshiki solution.")
    return {"text": _render_solution_text(p, req.solved)}

