"""Shared Futoshiki types, I/O, and CSP helpers for solvers and GUI."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

Cell = Tuple[int, int]
TraceEvent = Tuple[str, int, int, int]  # action, row, col, value


@dataclass
class Puzzle:
    n: int
    grid: List[List[int]]
    hcons: List[List[int]]
    vcons: List[List[int]]


@dataclass
class SolveResult:
    solved_grid: Optional[List[List[int]]]
    runtime_sec: float
    nodes_expanded: int
    memory_kb: float
    contradiction: bool = False
    # Optional diagnostics for GUI / demos (backward compatible defaults).
    messages: List[str] = field(default_factory=list)
    # Optional per-step search trace for GUI replay.
    trace: List[TraceEvent] = field(default_factory=list)


def parse_csv_line(line: str) -> List[int]:
    return [int(x.strip()) for x in line.split(",")]


def read_input(path: str) -> Puzzle:
    with open(path, "r", encoding="utf-8") as f:
        raw = [ln.strip() for ln in f.readlines()]
    lines = [ln for ln in raw if ln and not ln.startswith("#")]
    n = int(lines[0])
    idx = 1
    grid = [parse_csv_line(lines[idx + r]) for r in range(n)]
    idx += n
    hcons = [parse_csv_line(lines[idx + r]) for r in range(n)]
    idx += n
    vcons = [parse_csv_line(lines[idx + r]) for r in range(n - 1)]
    return Puzzle(n, grid, hcons, vcons)


def write_output(path: str, p: Puzzle, solved: List[List[int]]) -> None:
    lines: List[str] = []
    for i in range(p.n):
        row: List[str] = []
        for j in range(p.n):
            row.append(str(solved[i][j]))
            if j < p.n - 1:
                c = p.hcons[i][j]
                row.append("<" if c == 1 else ">" if c == -1 else " ")
        lines.append(" ".join(row))
        if i < p.n - 1:
            vr: List[str] = []
            for j in range(p.n):
                c = p.vcons[i][j]
                vr.append("^" if c == 1 else "v" if c == -1 else " ")
                if j < p.n - 1:
                    vr.append(" ")
            lines.append(" ".join(vr))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def neighbors(n: int, cell: Cell) -> List[Cell]:
    i, j = cell
    out: List[Cell] = []
    for jj in range(n):
        if jj != j:
            out.append((i, jj))
    for ii in range(n):
        if ii != i:
            out.append((ii, j))
    return out


def build_domains(p: Puzzle) -> Dict[Cell, Set[int]]:
    vals = set(range(1, p.n + 1))
    d: Dict[Cell, Set[int]] = {}
    for i in range(p.n):
        for j in range(p.n):
            d[(i, j)] = {p.grid[i][j]} if p.grid[i][j] != 0 else set(vals)
    return d


def inequality_ok(left: int, right: int, rel: int) -> bool:
    if rel == 1:
        return left < right
    if rel == -1:
        return left > right
    return True


def revise_ineq(dom: Dict[Cell, Set[int]], a: Cell, b: Cell, rel: int) -> bool:
    changed = False
    for va in list(dom[a]):
        if not any(inequality_ok(va, vb, rel) for vb in dom[b]):
            dom[a].remove(va)
            changed = True
    return changed


def ac3(p: Puzzle, dom: Dict[Cell, Set[int]]) -> bool:
    from collections import deque

    q = deque()
    n = p.n
    for i in range(n):
        for j in range(n):
            c = (i, j)
            for nb in neighbors(n, c):
                q.append((c, nb, 0))
            if j < n - 1 and p.hcons[i][j] != 0:
                q.append(((i, j), (i, j + 1), p.hcons[i][j]))
                q.append(((i, j + 1), (i, j), -p.hcons[i][j]))
            if i < n - 1 and p.vcons[i][j] != 0:
                q.append(((i, j), (i + 1, j), p.vcons[i][j]))
                q.append(((i + 1, j), (i, j), -p.vcons[i][j]))
    while q:
        xi, xj, rel = q.popleft()
        changed = False
        if rel == 0:
            if len(dom[xj]) == 1:
                only = next(iter(dom[xj]))
                if only in dom[xi] and len(dom[xi]) > 1:
                    dom[xi].remove(only)
                    changed = True
        else:
            changed = revise_ineq(dom, xi, xj, rel)
        if len(dom[xi]) == 0:
            return False
        if changed:
            for xk in neighbors(n, xi):
                if xk != xj:
                    q.append((xk, xi, 0))
    return True


def domains_to_assignment(dom: Dict[Cell, Set[int]]) -> Dict[Cell, int]:
    return {c: next(iter(ds)) for c, ds in dom.items() if len(ds) == 1}


def consistent_partial(p: Puzzle, asg: Dict[Cell, int], cell: Cell, val: int) -> bool:
    i, j = cell
    for jj in range(p.n):
        if jj != j and asg.get((i, jj)) == val:
            return False
    for ii in range(p.n):
        if ii != i and asg.get((ii, j)) == val:
            return False
    if j < p.n - 1 and (i, j + 1) in asg and not inequality_ok(val, asg[(i, j + 1)], p.hcons[i][j]):
        return False
    if j > 0 and (i, j - 1) in asg and not inequality_ok(asg[(i, j - 1)], val, p.hcons[i][j - 1]):
        return False
    if i < p.n - 1 and (i + 1, j) in asg and not inequality_ok(val, asg[(i + 1, j)], p.vcons[i][j]):
        return False
    if i > 0 and (i - 1, j) in asg and not inequality_ok(asg[(i - 1, j)], val, p.vcons[i - 1][j]):
        return False
    return True


def build_domains_from_partial(p: Puzzle, asg: Dict[Cell, int]) -> Optional[Dict[Cell, Set[int]]]:
    """
    Start from puzzle-consistent domains (same as build_domains), pin cells in `asg`,
    then run AC-3. Avoids over-pruning empty cells by row/column givens alone before AC-3.
    """
    d = build_domains(p)
    for c, v in asg.items():
        d[c] = {v}
    if not ac3(p, d):
        return None
    return d


def cell_candidates(p: Puzzle, asg: Dict[Cell, int], cell: Cell) -> List[int]:
    """Values still allowed for empty cell under partial assignment (row/col + inequality)."""
    i, j = cell
    if p.grid[i][j] != 0:
        return [p.grid[i][j]]
    cand = set(range(1, p.n + 1))
    for jj in range(p.n):
        t = asg.get((i, jj))
        if t is not None:
            cand.discard(t)
    for ii in range(p.n):
        t = asg.get((ii, j))
        if t is not None:
            cand.discard(t)
    out: List[int] = []
    for v in sorted(cand):
        if consistent_partial(p, asg, cell, v):
            out.append(v)
    return out


def choose_mrv(dom: Dict[Cell, Set[int]], asg: Dict[Cell, int]) -> Cell:
    return min((c for c in dom if c not in asg), key=lambda c: len(dom[c]))


def assignment_to_grid(p: Puzzle, asg: Dict[Cell, int]) -> List[List[int]]:
    return [[asg[(i, j)] for j in range(p.n)] for i in range(p.n)]


def is_valid_solution(p: Puzzle, g: List[List[int]]) -> bool:
    """Latin square 1..n plus horizontal/vertical inequality constraints."""
    n = p.n
    for i in range(n):
        row = [g[i][j] for j in range(n)]
        if sorted(row) != list(range(1, n + 1)):
            return False
    for j in range(n):
        col = [g[i][j] for i in range(n)]
        if sorted(col) != list(range(1, n + 1)):
            return False
    for i in range(n):
        for j in range(n):
            if p.grid[i][j] != 0 and g[i][j] != p.grid[i][j]:
                return False
    for i in range(n):
        for j in range(n - 1):
            rel = p.hcons[i][j]
            if rel != 0 and not inequality_ok(g[i][j], g[i][j + 1], rel):
                return False
    for i in range(n - 1):
        for j in range(n):
            rel = p.vcons[i][j]
            if rel != 0 and not inequality_ok(g[i][j], g[i + 1][j], rel):
                return False
    return True
