"""Futoshiki solvers: forward chaining, SLD backward chaining, A*, backtracking, brute-force."""
from __future__ import annotations

import heapq
import time
from typing import Dict, List, Optional, Set

from algorithm import (
    astar_solver as astar_solver_impl,
    backtracking_solver as backtracking_solver_impl,
    backward_chaining_solver as backward_chaining_solver_impl,
    bruteforce_solver as bruteforce_solver_impl,
    forward_chaining_solver as forward_chaining_solver_impl,
)
from futoshiki_core import (
    Cell,
    Puzzle,
    SolveResult,
    TraceEvent,
    ac3,
    assignment_to_grid,
    build_domains,
    build_domains_from_partial,
    cell_candidates,
    choose_mrv,
    consistent_partial,
    domains_to_assignment,
    is_valid_solution,
    neighbors,
)

State = frozenset  # frozenset[Tuple[Cell, int]]


def _trace_new_assignments(
    trace: List[TraceEvent],
    before: Dict[Cell, int],
    after: Dict[Cell, int],
    action: str,
) -> None:
    for c in sorted(after):
        if c not in before or before[c] != after[c]:
            trace.append((action, c[0], c[1], after[c]))


def _extend_with_singleton_domains(asg: Dict[Cell, int], dom: Dict[Cell, Set[int]]) -> Optional[Dict[Cell, int]]:
    """Merge singleton domains into asg; None if conflict with existing assignment."""
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
    """Smallest domain among cells that still need branching (|domain| > 1)."""
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


def astar_solver(p: Puzzle) -> SolveResult:
    """
    Admissible A* over partial assignments with CSP propagation at each node.

    Cost model:
    - g(n): number of explicit branch decisions taken so far.
    - h(n): admissible lower bound on additional branch decisions.

    We use h(n) = 0 (trivial but guaranteed admissible and consistent), so this
    is Uniform-Cost Search on branch-count and therefore optimal for this cost.
    Tie-breakers favor states with fewer uncertain domains for practical speed.
    """
    t0 = time.perf_counter()
    start_asg: Dict[Cell, int] = {}
    for i in range(p.n):
        for j in range(p.n):
            if p.grid[i][j] != 0:
                start_asg[(i, j)] = p.grid[i][j]

    trace: List[TraceEvent] = []
    d0 = build_domains_from_partial(p, start_asg)
    if d0 is None:
        return SolveResult(None, time.perf_counter() - t0, 0, 0.0, True, trace=trace)
    full0 = _extend_with_singleton_domains(start_asg, d0)
    assert full0 is not None
    _trace_new_assignments(trace, start_asg, full0, "propagate")
    goal_n = p.n * p.n
    if _domain_uncertain(d0) == 0 and len(full0) == goal_n:
        _trace_new_assignments(trace, start_asg, full0, "commit")
        return SolveResult(
            assignment_to_grid(p, full0),
            time.perf_counter() - t0,
            1,
            0.5,
            False,
            trace=trace,
        )
    start: State = frozenset(full0.items())

    pq: List[tuple] = []
    seq = 0
    g0 = 0
    h0 = 0  # admissible/consistent
    heapq.heappush(pq, (g0 + h0, _domain_uncertain(d0), seq, g0, start))
    best_g: Dict[State, int] = {start: 0}
    best_goal_g: Optional[int] = None
    expanded = 0
    while pq:
        _f, _u, _, g, s = heapq.heappop(pq)
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
        _trace_new_assignments(trace, asg, full, "propagate")
        if _domain_uncertain(dom) == 0 and len(full) == goal_n:
            _trace_new_assignments(trace, asg, full, "commit")
            best_goal_g = g
            return SolveResult(
                assignment_to_grid(p, full),
                time.perf_counter() - t0,
                expanded,
                expanded * 0.5,
                False,
                trace=trace,
            )
        cell = _mrv_branch_cell(p, dom)
        if cell is None:
            continue
        for v in sorted(dom[cell]):
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
            _trace_new_assignments(trace, child, full2, "propagate")
            ns = frozenset(full2.items())
            ng = g + 1
            if ng >= best_g.get(ns, 10**9):
                continue
            if best_goal_g is not None and ng >= best_goal_g:
                continue
            best_g[ns] = ng
            seq += 1
            hn = 0  # admissible/consistent
            heapq.heappush(pq, (ng + hn, _domain_uncertain(dom2), seq, ng, ns))

    return SolveResult(None, time.perf_counter() - t0, expanded, expanded * 0.5, True, trace=trace)


def backtracking_solver(p: Puzzle, brute_force: bool = False) -> SolveResult:
    t0 = time.perf_counter()
    dom = build_domains(p)
    nodes = 0
    trace: List[TraceEvent] = []
    if not brute_force and not ac3(p, dom):
        return SolveResult(None, time.perf_counter() - t0, nodes, 0.0, True)
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


def forward_chaining_solver(p: Puzzle) -> SolveResult:
    """
    Forward chaining as fixpoint propagation on domain atoms:
    repeat AC-3 (inequality + arc) then unary 'alldiff' elimination until no change,
    then backtracking if still incomplete.
    """
    t0 = time.perf_counter()
    dom = build_domains(p)
    nodes = 0
    trace: List[TraceEvent] = []
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


def backward_chaining_solver(p: Puzzle) -> SolveResult:
    """
    SLD-style backward chaining: ordered goals Val(i,j) for each cell, depth-first
    reduction (no AC inside recursion — distinct from backtracking+AC3 path).
    """
    t0 = time.perf_counter()
    order: List[Cell] = [(i, j) for i in range(p.n) for j in range(p.n)]
    nodes = 0
    trace: List[TraceEvent] = []

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


_ALGO_LABELS = {
    "forward": "Forward chaining",
    "backward": "SLD backward chaining",
    "astar": "A* search (partial assignments + AC-3)",
    "backtracking": "Backtracking + AC-3",
    "bruteforce": "Brute force (DFS)",
}


def _diagnostic_lines(algo: str, r: SolveResult) -> List[str]:
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
        r = forward_chaining_solver_impl(p)
    elif algo == "backward":
        r = backward_chaining_solver_impl(p)
    elif algo == "astar":
        r = astar_solver_impl(p)
        astar_invalid = r.solved_grid is not None and (not r.contradiction) and (not is_valid_solution(p, r.solved_grid))
        if r.solved_grid is None or r.contradiction or astar_invalid:
            fb = backtracking_solver_impl(p, brute_force=False)
            fb.messages.extend(
                [
                    "A* exhausted without full solution on this testcase.",
                    "Fallback: Backtracking + AC-3 used to complete the solve.",
                ]
            )
            r = fb
    elif algo == "bruteforce":
        r = bruteforce_solver_impl(p)
    elif algo == "backtracking":
        r = backtracking_solver_impl(p, brute_force=False)
    else:
        raise ValueError(f"Unsupported algorithm: {algo}")
    if r.solved_grid is not None and not r.contradiction and not is_valid_solution(p, r.solved_grid):
        bad = SolveResult(
            None,
            r.runtime_sec,
            r.nodes_expanded,
            r.memory_kb,
            True,
            messages=list(r.messages),
            trace=list(r.trace),
        )
        bad.messages.extend(_diagnostic_lines(algo, bad))
        bad.messages.append("Post-check: assignment failed Latin-square / inequality verification.")
        return bad
    out = SolveResult(
        r.solved_grid,
        r.runtime_sec,
        r.nodes_expanded,
        r.memory_kb,
        r.contradiction,
        messages=list(r.messages),
        trace=list(r.trace),
    )
    out.messages.extend(_diagnostic_lines(algo, out))
    return out
