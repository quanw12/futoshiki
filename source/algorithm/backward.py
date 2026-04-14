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

    def sld(k: int, asg: Dict[Cell, int]) -> Optional[Dict[Cell, int]]:
        nonlocal nodes
        nodes += 1
        if k == len(order):
            return asg
        c = order[k]
        if c in asg:
            return sld(k + 1, asg)
        for v in cell_candidates(p, asg, c):
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
