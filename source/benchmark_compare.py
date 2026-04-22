"""Run solver benchmark on inputs and regenerate outputs."""

from __future__ import annotations

import json
import multiprocessing
import time
from pathlib import Path
from typing import Any, Dict

from futoshiki_core import Puzzle, is_valid_solution, read_input, write_output
from solvers import solve

ALGOS = ["forward", "backward", "astar", "backtracking", "bruteforce"]
DEFAULT_TIMEOUT_SEC = 300
ALGO_TIMEOUT_SEC = {
    "forward": 300,
    "backward": 300,
    "astar": 300,
    "backtracking": 300,
    "bruteforce": 300,
}


def _solve_worker(algo: str, puzzle_data: Dict[str, Any], queue: multiprocessing.Queue) -> None:
    p = Puzzle(
        puzzle_data["n"],
        [row[:] for row in puzzle_data["grid"]],
        [row[:] for row in puzzle_data["hcons"]],
        [row[:] for row in puzzle_data["vcons"]],
    )
    result = solve(p, algo)
    queue.put(
        {
            "solved_grid": result.solved_grid,
            "runtime_sec": result.runtime_sec,
            "nodes_expanded": result.nodes_expanded,
            "memory_kb": result.memory_kb,
            "contradiction": result.contradiction,
            "messages": list(result.messages),
            "trace_len": len(result.trace),
        }
    )


def run_with_timeout(p: Puzzle, algo: str, timeout_sec: int) -> Dict[str, Any]:
    queue: multiprocessing.Queue = multiprocessing.Queue(maxsize=1)
    proc = multiprocessing.Process(
        target=_solve_worker,
        args=(
            algo,
            {"n": p.n, "grid": p.grid, "hcons": p.hcons, "vcons": p.vcons},
            queue,
        ),
        daemon=True,
    )
    t0 = time.perf_counter()
    proc.start()
    proc.join(timeout=timeout_sec)
    wall = time.perf_counter() - t0

    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=2)
        return {
            "solved_grid": None,
            "runtime_sec": wall,
            "nodes_expanded": 0,
            "memory_kb": 0.0,
            "contradiction": True,
            "messages": [f"Timed out after {timeout_sec}s"],
            "trace_len": 0,
            "timeout": True,
        }
    if queue.empty():
        return {
            "solved_grid": None,
            "runtime_sec": wall,
            "nodes_expanded": 0,
            "memory_kb": 0.0,
            "contradiction": True,
            "messages": ["Solver terminated without returning a result"],
            "trace_len": 0,
            "timeout": False,
        }
    out = queue.get()
    out["timeout"] = False
    out["runtime_wall_sec"] = wall
    return out


def write_failure_output(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# UNSOLVED\n# {message}\n", encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    inputs_dir = root / "inputs"
    outputs_dir = root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {"inputs_dir": str(inputs_dir), "timeouts_sec": ALGO_TIMEOUT_SEC, "cases": []}

    for idx in range(1, 11):
        input_name = f"input-{idx:02d}.txt"
        p = read_input(str(inputs_dir / input_name))
        case: Dict[str, Any] = {"input": input_name, "n": p.n, "algorithms": {}}

        canonical_grid = None
        for algo in ALGOS:
            timeout_sec = ALGO_TIMEOUT_SEC.get(algo, DEFAULT_TIMEOUT_SEC)
            result = run_with_timeout(p, algo, timeout_sec)
            solved_grid = result.get("solved_grid")
            valid = bool(solved_grid) and is_valid_solution(p, solved_grid)
            case["algorithms"][algo] = {
                "timeout": bool(result.get("timeout", False)),
                "runtime_sec": float(result.get("runtime_sec", 0.0)),
                "runtime_wall_sec": float(result.get("runtime_wall_sec", result.get("runtime_sec", 0.0))),
                "nodes_expanded": int(result.get("nodes_expanded", 0)),
                "trace_len": int(result.get("trace_len", 0)),
                "contradiction": bool(result.get("contradiction", True)),
                "valid": valid,
            }

            algo_out_path = outputs_dir / f"{algo}-output-{idx:02d}.txt"
            if valid:
                write_output(str(algo_out_path), p, solved_grid)
                if algo == "backtracking":
                    canonical_grid = solved_grid
            else:
                why = "timeout" if result.get("timeout", False) else "invalid-or-unsolved"
                write_failure_output(algo_out_path, f"{algo}: {why}")

        # Canonical output-XX is based on backtracking pure run for consistency.
        canonical_path = outputs_dir / f"output-{idx:02d}.txt"
        if canonical_grid is None:
            raise RuntimeError(f"Backtracking failed to produce a valid canonical solution for {input_name}")
        write_output(str(canonical_path), p, canonical_grid)

        summary["cases"].append(case)
        print(f"[OK] {input_name} -> output-{idx:02d}.txt")

    summary_path = outputs_dir / "benchmark-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Benchmark summary written to: {summary_path}")


if __name__ == "__main__":
    main()
