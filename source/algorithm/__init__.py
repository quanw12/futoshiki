"""Algorithm package for Futoshiki solvers."""

from __future__ import annotations

from futoshiki_core import Puzzle, SolveResult, is_valid_solution

from .astar import astar_solver
from .backtracking import backtracking_solver
from .backward import backward_chaining_solver
from .bruteforce import bruteforce_solver
from .forward import forward_chaining_solver

_ALGO_LABELS = {
    "forward": "Forward chaining",
    "backward": "SLD backward chaining",
    "astar": "A* search (partial assignments + AC-3)",
    "backtracking": "Backtracking + AC-3",
    "bruteforce": "Brute force (DFS)",
}


def _diagnostic_lines(algo: str, r: SolveResult) -> list[str]:
    label = _ALGO_LABELS.get(algo, algo)
    lines = [
        f"{label} finished in {r.runtime_sec:.4f}s.",
        f"Nodes / propagation steps: {r.nodes_expanded}",
        f"Memory estimate: {r.memory_kb:.1f} KB",
    ]
    if r.contradiction or r.solved_grid is None:
        lines.append("Result: no complete solution (contradiction or exhausted search).")
    else:
        lines.append("Result: verified full grid.")
    return lines


def solve(p: Puzzle, algo: str) -> SolveResult:
    if algo == "forward":
        result = forward_chaining_solver(p)
    elif algo == "backward":
        result = backward_chaining_solver(p)
    elif algo == "astar":
        result = astar_solver(p)
    elif algo == "bruteforce":
        result = bruteforce_solver(p)
    elif algo == "backtracking":
        result = backtracking_solver(p, brute_force=False)
    else:
        raise ValueError(f"Unsupported algorithm: {algo}")

    if result.solved_grid is not None and not result.contradiction and not is_valid_solution(p, result.solved_grid):
        invalid = SolveResult(
            None,
            result.runtime_sec,
            result.nodes_expanded,
            result.memory_kb,
            True,
            messages=list(result.messages),
            trace=list(result.trace),
        )
        invalid.messages.extend(_diagnostic_lines(algo, invalid))
        invalid.messages.append("Post-check: assignment failed Latin-square / inequality verification.")
        return invalid

    out = SolveResult(
        result.solved_grid,
        result.runtime_sec,
        result.nodes_expanded,
        result.memory_kb,
        result.contradiction,
        messages=list(result.messages),
        trace=list(result.trace),
    )
    out.messages.extend(_diagnostic_lines(algo, out))
    return out


__all__ = [
    "astar_solver",
    "backtracking_solver",
    "backward_chaining_solver",
    "bruteforce_solver",
    "forward_chaining_solver",
    "solve",
]
