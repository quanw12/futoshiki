"""Forward chaining solver with propagation only (pure mode)."""

from __future__ import annotations

import time

from futoshiki_core import Puzzle, SolveResult, TraceEvent, ac3, assignment_to_grid, build_domains, domains_to_assignment, neighbors

def _trace_new_assignments(
    trace: list[TraceEvent],
    before: dict,
    after: dict,
    action: str,
) -> None:
    for c in sorted(after):
        if c not in before or before[c] != after[c]:
            trace.append((action, c[0], c[1], after[c]))


def _apply_hidden_singles(p: Puzzle, dom: dict, trace: list[TraceEvent]) -> bool:
    """
    Forward-only inference: if a value can appear in exactly one cell of a row/col,
    force that cell to the value.
    """
    changed = False
    n = p.n
    for i in range(n):
        for v in range(1, n + 1):
            spots = [(i, j) for j in range(n) if v in dom[(i, j)]]
            if len(spots) == 1:
                c = spots[0]
                if len(dom[c]) > 1:
                    dom[c] = {v}
                    trace.append(("propagate", c[0], c[1], v))
                    changed = True
    for j in range(n):
        for v in range(1, n + 1):
            spots = [(i, j) for i in range(n) if v in dom[(i, j)]]
            if len(spots) == 1:
                c = spots[0]
                if len(dom[c]) > 1:
                    dom[c] = {v}
                    trace.append(("propagate", c[0], c[1], v))
                    changed = True
    return changed


def _apply_naked_pairs(p: Puzzle, dom: dict) -> bool:
    """
    If two cells in a row/col share the same 2-value domain {a,b},
    then remove a,b from all other cells in that unit.
    """
    changed = False
    n = p.n
    for i in range(n):
        pair_map: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for j in range(n):
            s = dom[(i, j)]
            if len(s) == 2:
                key = tuple(sorted(s))
                pair_map.setdefault(key, []).append((i, j))
        for pair, cells in pair_map.items():
            if len(cells) != 2:
                continue
            pair_vals = set(pair)
            for j in range(n):
                c = (i, j)
                if c in cells or len(dom[c]) <= 1:
                    continue
                before = len(dom[c])
                dom[c] -= pair_vals
                if len(dom[c]) != before:
                    changed = True
    for j in range(n):
        pair_map = {}
        for i in range(n):
            s = dom[(i, j)]
            if len(s) == 2:
                key = tuple(sorted(s))
                pair_map.setdefault(key, []).append((i, j))
        for pair, cells in pair_map.items():
            if len(cells) != 2:
                continue
            pair_vals = set(pair)
            for i in range(n):
                c = (i, j)
                if c in cells or len(dom[c]) <= 1:
                    continue
                before = len(dom[c])
                dom[c] -= pair_vals
                if len(dom[c]) != before:
                    changed = True
    return changed


def _clone_domains(dom: dict) -> dict:
    return {c: set(vals) for c, vals in dom.items()}


def _apply_singleton_probing(p: Puzzle, dom: dict, trace: list[TraceEvent]) -> bool:
    """
    For each candidate value, assume it and run AC-3.
    If assumption leads to contradiction, that value is impossible and can be removed.
    """
    changed = False
    for c in sorted(dom):
        if len(dom[c]) <= 1:
            continue
        for v in sorted(list(dom[c])):
            trial = _clone_domains(dom)
            trial[c] = {v}
            if not ac3(p, trial):
                dom[c].remove(v)
                trace.append(("reject", c[0], c[1], v))
                changed = True
                if len(dom[c]) == 0:
                    return changed
        if len(dom[c]) == 1:
            only = next(iter(dom[c]))
            trace.append(("propagate", c[0], c[1], only))
    return changed


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
        if _apply_hidden_singles(p, dom, trace):
            changed = True
        if _apply_naked_pairs(p, dom):
            changed = True
            for c, ds in dom.items():
                if len(ds) == 0:
                    return SolveResult(None, time.perf_counter() - t0, nodes, nodes * 0.3, True, trace=trace)
        if _apply_singleton_probing(p, dom, trace):
            changed = True
            for c, ds in dom.items():
                if len(ds) == 0:
                    return SolveResult(None, time.perf_counter() - t0, nodes, nodes * 0.3, True, trace=trace)
        if not changed:
            break
    asg = domains_to_assignment(dom)
    if len(asg) < p.n * p.n:
        return SolveResult(
            None,
            time.perf_counter() - t0,
            nodes,
            nodes * 0.3,
            False,
            messages=["Forward chaining reached fixpoint without complete assignment."],
            trace=trace,
        )
    _trace_new_assignments(trace, known, asg, "commit")
    return SolveResult(assignment_to_grid(p, asg), time.perf_counter() - t0, nodes, nodes * 0.3, False, trace=trace)
