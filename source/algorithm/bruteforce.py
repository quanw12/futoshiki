"""Brute-force solver wrapper."""

from __future__ import annotations

from futoshiki_core import Puzzle, SolveResult

from .backtracking import backtracking_solver


def bruteforce_solver(p: Puzzle) -> SolveResult:
    return backtracking_solver(p, brute_force=True)
