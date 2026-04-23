"""Fast A* solver (CSP heuristic + MRV tie-break)."""

from __future__ import annotations

import heapq
import time
from typing import Dict, Optional, Set

from futoshiki_core import (
    Cell,
    Puzzle,
    SolveResult,
    TraceEvent,
    assignment_to_grid,
    build_domains_from_partial,
    consistent_partial,
    is_valid_solution,
)

State = frozenset  # frozenset[Tuple[Cell, int]]


def _trace_new_assignments(
    trace: list[TraceEvent],
    before: Dict[Cell, int],
    after: Dict[Cell, int],
    action: str,
) -> None:
    for c in sorted(after):
        if c not in before or before[c] != after[c]:
            trace.append((action, c[0], c[1], after[c]))


def _extend_with_singleton_domains(asg: Dict[Cell, int], dom: Dict[Cell, Set[int]]) -> Optional[Dict[Cell, int]]:
    out = dict(asg)
    for c, s in dom.items():
        if len(s) == 1:
            v = next(iter(s))
            if c in out and out[c] != v:
                return None
            out[c] = v
    return out


def _domain_uncertain(dom: Dict[Cell, Set[int]]) -> int:
    return sum(1 for s in dom.values() if len(s) > 1)


def _mrv_branch_cell(p: Puzzle, dom: Dict[Cell, Set[int]]) -> Optional[Cell]:
    best: Optional[Cell] = None
    best_sz = 10**9
    for i in range(p.n):
        for j in range(p.n):
            c = (i, j)
            sz = len(dom[c])
            if sz <= 1:
                continue
            if sz < best_sz:
                best_sz = sz
                best = c
    return best


def _mrv_tiebreak(dom: Dict[Cell, Set[int]]) -> int:
    best_sz = 10**9
    for s in dom.values():
        sz = len(s)
        if sz > 1 and sz < best_sz:
            best_sz = sz
    return best_sz


def _admissible_h(uncertain_count: int, assigned_count: int, goal_n: int) -> int:
    """
    Admissible/consistent heuristic:
    - 0 at goal
    - 1 for any non-goal state

    Under our cost model (one branching decision costs 1), every non-goal
    state requires at least one additional decision to reach a complete
    assignment, so h=1 is a safe lower bound and not identically zero.
    """
    if uncertain_count == 0 and assigned_count == goal_n:
        return 0
    return 1


def _assignment_consistent(p: Puzzle, asg: Dict[Cell, int]) -> bool:
    """Validate pairwise row/col/inequality consistency for full/partial assignments."""
    for c, v in asg.items():
        other = dict(asg)
        other.pop(c, None)
        if not consistent_partial(p, other, c, v):
            return False
    return True


def astar_solver(p: Puzzle) -> SolveResult:
    # Official comparison mode uses an explicitly admissible heuristic.
    # h(s)=0 is a safe lower bound on remaining branch decisions.
    t0 = time.perf_counter()
    start_asg: Dict[Cell, int] = {}
    for i in range(p.n):
        for j in range(p.n):
            if p.grid[i][j] != 0:
                start_asg[(i, j)] = p.grid[i][j]

    trace: list[TraceEvent] = []
    d0 = build_domains_from_partial(p, start_asg)
    if d0 is None:
        return SolveResult(None, time.perf_counter() - t0, 0, 0.0, True, trace=trace)
    full0 = _extend_with_singleton_domains(start_asg, d0)
    assert full0 is not None
    if not _assignment_consistent(p, full0):
        return SolveResult(None, time.perf_counter() - t0, 0, 0.0, True, trace=trace)
    _trace_new_assignments(trace, start_asg, full0, "propagate")
    goal_n = p.n * p.n
    if _domain_uncertain(d0) == 0 and len(full0) == goal_n:
        g0 = assignment_to_grid(p, full0)
        if is_valid_solution(p, g0):
            _trace_new_assignments(trace, start_asg, full0, "commit")
            return SolveResult(g0, time.perf_counter() - t0, 1, 0.5, False, trace=trace)
        return SolveResult(None, time.perf_counter() - t0, 1, 0.5, True, trace=trace)
    start: State = frozenset(full0.items())

    pq: list[tuple] = []
    seq = 0
    g0 = 0
    h0 = _admissible_h(_domain_uncertain(d0), len(full0), goal_n)
    heapq.heappush(pq, (g0 + h0, _mrv_tiebreak(d0), h0, seq, g0, start))
    best_g: Dict[State, int] = {start: 0}
    best_goal_g: Optional[int] = None
    expanded = 0
    while pq:
        _f, _mrv, _u, _, g, s = heapq.heappop(pq)
        if g > best_g.get(s, 10**9):
            continue
        if best_goal_g is not None and g >= best_goal_g:
            continue
        expanded += 1
        asg = dict(s)
        dom = build_domains_from_partial(p, asg)
        if dom is None:
            continue
        full = _extend_with_singleton_domains(asg, dom)
        if full is None:
            continue
        if not _assignment_consistent(p, full):
            continue
        _trace_new_assignments(trace, asg, full, "propagate")
        if _domain_uncertain(dom) == 0 and len(full) == goal_n:
            solved = assignment_to_grid(p, full)
            if is_valid_solution(p, solved):
                _trace_new_assignments(trace, asg, full, "commit")
                best_goal_g = g
                return SolveResult(solved, time.perf_counter() - t0, expanded, expanded * 0.5, False, trace=trace)
            continue
        cell = _mrv_branch_cell(p, dom)
        if cell is None:
            continue
        for v in sorted(dom[cell]):
            if not consistent_partial(p, full, cell, v):
                trace.append(("reject", cell[0], cell[1], v))
                continue
            child = dict(full)
            child[cell] = v
            trace.append(("set", cell[0], cell[1], v))
            dom2 = build_domains_from_partial(p, child)
            if dom2 is None:
                trace.append(("reject", cell[0], cell[1], v))
                continue
            full2 = _extend_with_singleton_domains(child, dom2)
            if full2 is None:
                trace.append(("reject", cell[0], cell[1], v))
                continue
            if not _assignment_consistent(p, full2):
                trace.append(("reject", cell[0], cell[1], v))
                continue
            _trace_new_assignments(trace, child, full2, "propagate")
            ns = frozenset(full2.items())
            ng = g + 1
            if ng >= best_g.get(ns, 10**9):
                continue
            if best_goal_g is not None and ng >= best_goal_g:
                continue
            best_g[ns] = ng
            seq += 1
            hn = _admissible_h(_domain_uncertain(dom2), len(full2), goal_n)
            heapq.heappush(pq, (ng + hn, _mrv_tiebreak(dom2), hn, seq, ng, ns))

    return SolveResult(None, time.perf_counter() - t0, expanded, expanded * 0.5, True, trace=trace)
