"""SLD-style backward chaining solver."""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from futoshiki_core import Cell, Puzzle, SolveResult, TraceEvent, assignment_to_grid, cell_candidates


def backward_chaining_solver(p: Puzzle) -> SolveResult:
    t0 = time.perf_counter()
    order: List[Cell] = [(i, j) for i in range(p.n) for j in range(p.n)]
    nodes = 0
    trace: list[TraceEvent] = []

    def pick_next_goal(asg: Dict[Cell, int]) -> tuple[Optional[Cell], Optional[list[int]]]:
        best_cell: Optional[Cell] = None
        best_cands: Optional[list[int]] = None
        best_len = 10**9
        for c in order:
            if c in asg:
                continue
            cands = cell_candidates(p, asg, c)
            if len(cands) == 0:
                return c, []
            if len(cands) < best_len:
                best_len = len(cands)
                best_cell = c
                best_cands = cands
                if best_len == 1:
                    break
        return best_cell, best_cands

    def sld(k: int, asg: Dict[Cell, int]) -> Optional[Dict[Cell, int]]:
        nonlocal nodes
        nodes += 1
        if k == len(order):
            return asg
        c, cands = pick_next_goal(asg)
        if c is None:
            return asg
        if cands is None or len(cands) == 0:
            return None
        for v in cands:
            trace.append(("set", c[0], c[1], v))
            na = dict(asg)
            na[c] = v
            r = sld(k + 1, na)
            if r is not None:
                trace.append(("commit", c[0], c[1], v))
                return r
            trace.append(("unset", c[0], c[1], 0))
        return None

    start: Dict[Cell, int] = {}
    for i in range(p.n):
        for j in range(p.n):
            if p.grid[i][j] != 0:
                start[(i, j)] = p.grid[i][j]
    ans = sld(0, start)
    runtime = time.perf_counter() - t0
    if ans is None:
        return SolveResult(None, runtime, nodes, nodes * 0.5, True, trace=trace)
    return SolveResult(assignment_to_grid(p, ans), runtime, nodes, nodes * 0.5, False, trace=trace)
