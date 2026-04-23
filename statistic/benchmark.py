"""Unified benchmark runner: benchmark all algorithms and export CSV for Excel."""

from __future__ import annotations

import csv
import glob
import multiprocessing
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence

# Allow running from repo root or from this folder.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SOURCE_DIR = os.path.join(_REPO_ROOT, "source")
if _SOURCE_DIR not in sys.path:
    sys.path.insert(0, _SOURCE_DIR)

from algorithm import solve  # noqa: E402
from futoshiki_core import Puzzle, is_valid_solution, read_input  # noqa: E402

ALGOS = ["forward", "backward", "astar", "backtracking", "bruteforce"]
DEFAULT_TIMEOUT_SEC = 300
ALGO_TIMEOUT_SEC = {
    "forward": 300,
    "backward": 300,
    "astar": 300,
    "backtracking": 300,
    "bruteforce": 300,
}


@dataclass(frozen=True)
class BenchmarkRow:
    algorithm_name: str
    test_case_id: str
    solution_steps: int
    execution_time_ms: float
    nodes_expanded: int
    memory_usage_bytes: int
    status: str
    failed_reason: str


def _discover_inputs(repo_root: str) -> List[str]:
    pat = os.path.join(repo_root, "inputs", "input-*.txt")
    return sorted(glob.glob(pat))


def _test_case_id_from_path(path: str) -> str:
    base = os.path.basename(path)
    stem, _ = os.path.splitext(base)
    return stem


def _solution_steps_from_trace(trace: Sequence[tuple]) -> int:
    keep = {"set", "propagate", "commit"}
    steps = 0
    for ev in trace:
        if not ev:
            continue
        action = ev[0]
        if action not in keep:
            continue
        if len(ev) >= 4 and ev[3] == 0:
            continue
        steps += 1
    return steps


def _solve_worker(algo: str, puzzle_data: Dict[str, Any], queue: multiprocessing.Queue) -> None:
    try:
        p = Puzzle(
            puzzle_data["n"],
            [row[:] for row in puzzle_data["grid"]],
            [row[:] for row in puzzle_data["hcons"]],
            [row[:] for row in puzzle_data["vcons"]],
        )
        result = solve(p, algo)
        queue.put(
            {
                "ok": True,
                "solved_grid": result.solved_grid,
                "runtime_sec": result.runtime_sec,
                "nodes_expanded": result.nodes_expanded,
                "memory_kb": result.memory_kb,
                "contradiction": result.contradiction,
                "solution_steps": _solution_steps_from_trace(result.trace),
            }
        )
    except Exception as exc:  # noqa: BLE001
        queue.put({"ok": False, "error": str(exc)})


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
            "ok": False,
            "timeout": True,
            "runtime_sec": wall,
            "runtime_wall_sec": wall,
            "nodes_expanded": 0,
            "memory_kb": 0.0,
            "solution_steps": 0,
            "solved_grid": None,
            "contradiction": True,
            "error": f"Timed out after {timeout_sec}s",
        }

    if queue.empty():
        return {
            "ok": False,
            "timeout": False,
            "runtime_sec": wall,
            "runtime_wall_sec": wall,
            "nodes_expanded": 0,
            "memory_kb": 0.0,
            "solution_steps": 0,
            "solved_grid": None,
            "contradiction": True,
            "error": "Solver terminated without returning a result",
        }

    out = queue.get()
    out["timeout"] = False
    out["runtime_wall_sec"] = wall
    return out


def run_benchmark(input_paths: Iterable[str], algorithms: Sequence[str]) -> List[BenchmarkRow]:
    rows: List[BenchmarkRow] = []
    for path in input_paths:
        tc = _test_case_id_from_path(path)
        base_p = read_input(path)

        for algo in algorithms:
            timeout_sec = ALGO_TIMEOUT_SEC.get(algo, DEFAULT_TIMEOUT_SEC)
            out = run_with_timeout(base_p, algo, timeout_sec)

            solved_grid = out.get("solved_grid")
            valid = bool(solved_grid) and not out.get("contradiction", True) and is_valid_solution(base_p, solved_grid)

            if valid:
                status = "success"
                failed_reason = ""
            else:
                status = "failed"
                if out.get("timeout", False):
                    failed_reason = "timeout"
                elif not out.get("ok", True):
                    failed_reason = "runtime_error"
                elif out.get("contradiction", False):
                    failed_reason = "contradiction"
                elif solved_grid is None:
                    failed_reason = "exhausted_unsolved"
                else:
                    failed_reason = "invalid_solution"

            exec_sec = float(out.get("runtime_wall_sec", out.get("runtime_sec", 0.0)))
            rows.append(
                BenchmarkRow(
                    algorithm_name=algo,
                    test_case_id=tc,
                    solution_steps=int(out.get("solution_steps", 0)),
                    execution_time_ms=exec_sec * 1000.0,
                    nodes_expanded=int(out.get("nodes_expanded", 0)),
                    memory_usage_bytes=int(round(float(out.get("memory_kb", 0.0)) * 1024.0)),
                    status=status,
                    failed_reason=failed_reason,
                )
            )
    return rows


def export_csv(rows: Sequence[BenchmarkRow], out_path: str) -> None:
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "Algorithm",
                "TestCase",
                "SolutionSteps",
                "ExecutionTime(ms)",
                "NodesExpanded",
                "MemoryUsage(bytes)",
                "Status",
                "FailedReason",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r.algorithm_name,
                    r.test_case_id,
                    r.solution_steps,
                    f"{r.execution_time_ms:.3f}",
                    r.nodes_expanded,
                    r.memory_usage_bytes,
                    r.status,
                    r.failed_reason,
                ]
            )


def main() -> None:
    inputs = _discover_inputs(_REPO_ROOT)
    rows = run_benchmark(inputs, ALGOS)
    out_path = os.path.join(_REPO_ROOT, "benchmark_results.csv")
    export_csv(rows, out_path)
    print(f"Benchmark CSV written to: {out_path}")


if __name__ == "__main__":
    main()

