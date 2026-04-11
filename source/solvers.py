"""Futoshiki solvers: forward chaining, SLD backward chaining, A*, backtracking, brute-force."""
from __future__ import annotations

import heapq
import time
from typing import Dict, List, Optional, Set

from futoshiki_core import (
    Cell,
    Puzzle,
    SolveResult,
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
    A* over partial assignments with CSP propagation at each node:
    domains = AC-3(build from partial), then materialize all singleton domains.
    Branching uses MRV on cells with |domain| > 1 (same information as backtracking+AC3).
    """
    t0 = time.perf_counter()
    start_asg: Dict[Cell, int] = {}
    for i in range(p.n):
        for j in range(p.n):
            if p.grid[i][j] != 0:
                start_asg[(i, j)] = p.grid[i][j]

    d0 = build_domains_from_partial(p, start_asg)
    if d0 is None:
        return SolveResult(None, time.perf_counter() - t0, 0, 0.0, True)
    full0 = _extend_with_singleton_domains(start_asg, d0)
    assert full0 is not None
    goal_n = p.n * p.n
    if _domain_uncertain(d0) == 0 and len(full0) == goal_n:
        return SolveResult(
            assignment_to_grid(p, full0),
            time.perf_counter() - t0,
            1,
            0.5,
            False,
        )
    start: State = frozenset(full0.items())

    pq: List[tuple] = []
    seq = 0
    g0 = 0
    h0 = _domain_uncertain(d0)
    heapq.heappush(pq, (g0 + h0, seq, g0, start))
    best_g: Dict[State, int] = {start: 0}
    expanded = 0

    while pq:
        _f, _, g, s = heapq.heappop(pq)
        if g > best_g.get(s, 10**9):
            continue
        expanded += 1
        asg = dict(s)
        dom = build_domains_from_partial(p, asg)
        if dom is None:
            continue
        full = _extend_with_singleton_domains(asg, dom)
        if full is None:
            continue
        if _domain_uncertain(dom) == 0 and len(full) == goal_n:
            return SolveResult(
                assignment_to_grid(p, full),
                time.perf_counter() - t0,
                expanded,
                expanded * 0.5,
                False,
            )
        cell = _mrv_branch_cell(p, dom)
        if cell is None:
            continue
        for v in sorted(dom[cell]):
            child = dict(full)
            child[cell] = v
            dom2 = build_domains_from_partial(p, child)
            if dom2 is None:
                continue
            full2 = _extend_with_singleton_domains(child, dom2)
            if full2 is None:
                continue
            ns = frozenset(full2.items())
            ng = g + 1
            if ng >= best_g.get(ns, 10**9):
                continue
            best_g[ns] = ng
            seq += 1
            hn = _domain_uncertain(dom2)
            heapq.heappush(pq, (ng + hn, seq, ng, ns))

    return SolveResult(None, time.perf_counter() - t0, expanded, expanded * 0.5, True)


def backtracking_solver(p: Puzzle, brute_force: bool = False) -> SolveResult:
    t0 = time.perf_counter()
    dom = build_domains(p)
    nodes = 0
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
            if not consistent_partial(p, a, cell, v):
                continue
            a2 = dict(a)
            a2[cell] = v
            d2 = {k: set(x) for k, x in d.items()}
            d2[cell] = {v}
            if not brute_force:
                if not ac3(p, d2):
                    continue
                for c, sv in domains_to_assignment(d2).items():
                    if c in a2 and a2[c] != sv:
                        break
                    a2[c] = sv
                else:
                    ans = rec(d2, a2)
                    if ans is not None:
                        return ans
                    continue
            else:
                ans = rec(d2, a2)
                if ans is not None:
                    return ans
        return None

    ans = rec(dom, asg)
    runtime = time.perf_counter() - t0
    if ans is None:
        return SolveResult(None, runtime, nodes, nodes * 0.5, True)
    return SolveResult(assignment_to_grid(p, ans), runtime, nodes, nodes * 0.5, False)


def forward_chaining_solver(p: Puzzle) -> SolveResult:
    """
    Forward chaining as fixpoint propagation on domain atoms:
    repeat AC-3 (inequality + arc) then unary 'alldiff' elimination until no change,
    then backtracking if still incomplete.
    """
    t0 = time.perf_counter()
    dom = build_domains(p)
    nodes = 0
    while True:
        nodes += 1
        if not ac3(p, dom):
            return SolveResult(None, time.perf_counter() - t0, nodes, nodes * 0.3, True)
        changed = False
        singles = [c for c, ds in dom.items() if len(ds) == 1]
        for c in singles:
            v = next(iter(dom[c]))
            for nb in neighbors(p.n, c):
                if v in dom[nb] and len(dom[nb]) > 1:
                    dom[nb].remove(v)
                    changed = True
                    if len(dom[nb]) == 0:
                        return SolveResult(None, time.perf_counter() - t0, nodes, nodes * 0.3, True)
        if not changed:
            break
    asg = domains_to_assignment(dom)
    if len(asg) < p.n * p.n:
        bt = backtracking_solver(p, brute_force=False)
        bt.runtime_sec += time.perf_counter() - t0
        bt.nodes_expanded += nodes
        return bt
    return SolveResult(assignment_to_grid(p, asg), time.perf_counter() - t0, nodes, nodes * 0.3, False)


def backward_chaining_solver(p: Puzzle) -> SolveResult:
    """
    SLD-style backward chaining: ordered goals Val(i,j) for each cell, depth-first
    reduction (no AC inside recursion — distinct from backtracking+AC3 path).
    """
    t0 = time.perf_counter()
    order: List[Cell] = [(i, j) for i in range(p.n) for j in range(p.n)]
    nodes = 0

    def sld(k: int, asg: Dict[Cell, int]) -> Optional[Dict[Cell, int]]:
        nonlocal nodes
        nodes += 1
        if k == len(order):
            return asg
        c = order[k]
        if c in asg:
            return sld(k + 1, asg)
        for v in cell_candidates(p, asg, c):
            na = dict(asg)
            na[c] = v
            r = sld(k + 1, na)
            if r is not None:
                return r
        return None

    start: Dict[Cell, int] = {}
    for i in range(p.n):
        for j in range(p.n):
            if p.grid[i][j] != 0:
                start[(i, j)] = p.grid[i][j]
    ans = sld(0, start)
    runtime = time.perf_counter() - t0
    if ans is None:
        return SolveResult(None, runtime, nodes, nodes * 0.5, True)
    return SolveResult(assignment_to_grid(p, ans), runtime, nodes, nodes * 0.5, False)


def solve(p: Puzzle, algo: str) -> SolveResult:
    if algo == "forward":
        r = forward_chaining_solver(p)
    elif algo == "backward":
        r = backward_chaining_solver(p)
    elif algo == "astar":
        r = astar_solver(p)
    elif algo == "bruteforce":
        r = backtracking_solver(p, brute_force=True)
    elif algo == "backtracking":
        r = backtracking_solver(p, brute_force=False)
    else:
        raise ValueError(f"Unsupported algorithm: {algo}")
    if r.solved_grid is not None and not r.contradiction and not is_valid_solution(p, r.solved_grid):
        return SolveResult(None, r.runtime_sec, r.nodes_expanded, r.memory_kb, True)
    return r
