"""Backtracking-based solvers."""

from __future__ import annotations

import time
from typing import Dict, Optional, Set

from futoshiki_core import (
    Cell,
    Puzzle,
    SolveResult,
    TraceEvent,
    ac3,
    assignment_to_grid,
    build_domains,
    choose_mrv,
    consistent_partial,
    domains_to_assignment,
)


def backtracking_solver(p: Puzzle, brute_force: bool = False) -> SolveResult:
    t0 = time.perf_counter()
    dom = build_domains(p)
    nodes = 0
    trace: list[TraceEvent] = []
    if not brute_force and not ac3(p, dom):
        return SolveResult(None, time.perf_counter() - t0, nodes, 0.0, True, trace=trace)
    asg = domains_to_assignment(dom)

    def rec(d: Dict[Cell, Set[int]], a: Dict[Cell, int]) -> Optional[Dict[Cell, int]]:
        nonlocal nodes
        nodes += 1
        if len(a) == p.n * p.n:
            return a
        cell = next(c for c in d if c not in a) if brute_force else choose_mrv(d, a)
        values = range(1, p.n + 1) if brute_force else sorted(d[cell])
        for v in values:
            trace.append(("set", cell[0], cell[1], v))
            if not consistent_partial(p, a, cell, v):
                trace.append(("reject", cell[0], cell[1], v))
                continue
            a2 = dict(a)
            a2[cell] = v
            d2 = {k: set(x) for k, x in d.items()}
            d2[cell] = {v}
            if not brute_force:
                if not ac3(p, d2):
                    trace.append(("reject", cell[0], cell[1], v))
                    continue
                for c, sv in domains_to_assignment(d2).items():
                    if c in a2 and a2[c] != sv:
                        break
                    if c not in a2:
                        trace.append(("propagate", c[0], c[1], sv))
                    a2[c] = sv
                else:
                    ans = rec(d2, a2)
                    if ans is not None:
                        trace.append(("commit", cell[0], cell[1], v))
                        return ans
                    trace.append(("unset", cell[0], cell[1], 0))
                    continue
            else:
                ans = rec(d2, a2)
                if ans is not None:
                    trace.append(("commit", cell[0], cell[1], v))
                    return ans
                trace.append(("unset", cell[0], cell[1], 0))
        return None

    ans = rec(dom, asg)
    runtime = time.perf_counter() - t0
    if ans is None:
        return SolveResult(None, runtime, nodes, nodes * 0.5, True, trace=trace)
    return SolveResult(assignment_to_grid(p, ans), runtime, nodes, nodes * 0.5, False, trace=trace)
