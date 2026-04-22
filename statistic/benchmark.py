"""Headless benchmark runner (no UI): run all algorithms on all inputs and export CSV."""

from __future__ import annotations

import csv
import glob
import os
import sys
import time
from dataclasses import dataclass
from typing import Iterable, List, Sequence

# Allow running from repo root or from this folder.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "source"))

from futoshiki_core import Puzzle, is_valid_solution, read_input  # noqa: E402
from solvers import solve  # noqa: E402


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


def _clone_puzzle(p: Puzzle) -> Puzzle:
    return Puzzle(
        p.n,
        [row[:] for row in p.grid],
        [row[:] for row in p.hcons],
        [row[:] for row in p.vcons],
    )


def _discover_inputs(repo_root: str) -> List[str]:
    pat = os.path.join(repo_root, "inputs", "input-*.txt")
    return sorted(glob.glob(pat))


def _test_case_id_from_path(path: str) -> str:
    base = os.path.basename(path)
    stem, _ = os.path.splitext(base)
    return stem


def _solution_steps_from_trace(trace: Sequence[tuple]) -> int:
    """
    Uniform definition:
    count of value assignments performed (branch decisions + propagation + commits),
    excluding rejects/unsets.
    """
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


def run_benchmark(
    input_paths: Iterable[str],
    algorithms: Sequence[str],
) -> List[BenchmarkRow]:
    rows: List[BenchmarkRow] = []
    for path in input_paths:
        tc = _test_case_id_from_path(path)
        base_p = read_input(path)
        for algo in algorithms:
            p = _clone_puzzle(base_p)
            t0 = time.perf_counter_ns()
            r = solve(p, algo)
            t1 = time.perf_counter_ns()
            valid = bool(r.solved_grid) and (not r.contradiction) and is_valid_solution(p, r.solved_grid)
            if valid:
                status = "success"
                failed_reason = ""
            else:
                status = "failed"
                if r.contradiction:
                    failed_reason = "contradiction"
                elif r.solved_grid is None:
                    failed_reason = "exhausted_unsolved"
                else:
                    failed_reason = "invalid_solution"
            rows.append(
                BenchmarkRow(
                    algorithm_name=algo,
                    test_case_id=tc,
                    solution_steps=_solution_steps_from_trace(r.trace),
                    execution_time_ms=(t1 - t0) / 1_000_000.0,
                    nodes_expanded=int(r.nodes_expanded),
                    memory_usage_bytes=int(round((r.memory_kb or 0.0) * 1024.0)),
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
    repo_root = _REPO_ROOT
    inputs = _discover_inputs(repo_root)
    algos = ["forward", "backward", "astar", "backtracking", "bruteforce"]
    rows = run_benchmark(inputs, algos)
    export_csv(rows, os.path.join(repo_root, "benchmark_results.csv"))


if __name__ == "__main__":
    main()

