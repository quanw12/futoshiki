"""Forward chaining solver with propagation then fallback search."""

from __future__ import annotations

import time

from futoshiki_core import Puzzle, SolveResult, TraceEvent, ac3, assignment_to_grid, build_domains, domains_to_assignment, neighbors

from .backtracking import backtracking_solver


def _trace_new_assignments(
    trace: list[TraceEvent],
    before: dict,
    after: dict,
    action: str,
) -> None:
    for c in sorted(after):
        if c not in before or before[c] != after[c]:
            trace.append((action, c[0], c[1], after[c]))


def forward_chaining_solver(p: Puzzle) -> SolveResult:
    t0 = time.perf_counter()
    dom = build_domains(p)
    nodes = 0
    trace: list[TraceEvent] = []
    known = domains_to_assignment(dom)
    while True:
        nodes += 1
        if not ac3(p, dom):
            return SolveResult(None, time.perf_counter() - t0, nodes, nodes * 0.3, True, trace=trace)
        now = domains_to_assignment(dom)
        _trace_new_assignments(trace, known, now, "propagate")
        known = dict(now)
        changed = False
        singles = [c for c, ds in dom.items() if len(ds) == 1]
        for c in singles:
            v = next(iter(dom[c]))
            for nb in neighbors(p.n, c):
                if v in dom[nb] and len(dom[nb]) > 1:
                    dom[nb].remove(v)
                    changed = True
                    if len(dom[nb]) == 0:
                        return SolveResult(None, time.perf_counter() - t0, nodes, nodes * 0.3, True, trace=trace)
        if not changed:
            break
    asg = domains_to_assignment(dom)
    if len(asg) < p.n * p.n:
        bt = backtracking_solver(p, brute_force=False)
        bt.runtime_sec += time.perf_counter() - t0
        bt.nodes_expanded += nodes
        bt.trace = trace + list(bt.trace)
        return bt
    _trace_new_assignments(trace, known, asg, "commit")
    return SolveResult(assignment_to_grid(p, asg), time.perf_counter() - t0, nodes, nodes * 0.3, False, trace=trace)
