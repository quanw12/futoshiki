"""
Ground propositional CNF for a concrete Futoshiki instance (FOL → grounding).

Propositional atom X[i,j,v] (1-based DIMACS variable): cell (i,j) takes value v.
Indices: i,j in [0, N-1], v in [1, N].
"""
from __future__ import annotations

from typing import List, Tuple

from futoshiki_core import Puzzle

Clause = Tuple[int, ...]


def var_id(n: int, i: int, j: int, v: int) -> int:
    """1-based DIMACS id for X[i,j,v]."""
    return i * n * n + j * n + v


def build_ground_cnf_clauses(p: Puzzle) -> Tuple[int, List[Clause]]:
    """
    Return (num_vars, clauses) for this puzzle instance.
    num_vars = N^3 (all X[i,j,v]).
    """
    n = p.n
    num_vars = n * n * n
    clauses: List[Clause] = []

    # A1: each cell at least one value
    for i in range(n):
        for j in range(n):
            clauses.append(tuple(var_id(n, i, j, v) for v in range(1, n + 1)))

    # A2: each cell at most one value
    for i in range(n):
        for j in range(n):
            for v1 in range(1, n + 1):
                for v2 in range(v1 + 1, n + 1):
                    clauses.append((-var_id(n, i, j, v1), -var_id(n, i, j, v2)))

    # Row uniqueness: same value not in two columns of same row
    for i in range(n):
        for v in range(1, n + 1):
            for j1 in range(n):
                for j2 in range(j1 + 1, n):
                    clauses.append((-var_id(n, i, j1, v), -var_id(n, i, j2, v)))

    # Column uniqueness
    for j in range(n):
        for v in range(1, n + 1):
            for i1 in range(n):
                for i2 in range(i1 + 1, n):
                    clauses.append((-var_id(n, i1, j, v), -var_id(n, i2, j, v)))

    # Given clues
    for i in range(n):
        for j in range(n):
            g = p.grid[i][j]
            if g != 0:
                for v in range(1, n + 1):
                    if v != g:
                        clauses.append((-var_id(n, i, j, v),))

    # Horizontal inequalities
    for i in range(n):
        for j in range(n - 1):
            rel = p.hcons[i][j]
            if rel == 1:
                for v1 in range(1, n + 1):
                    for v2 in range(1, n + 1):
                        if not (v1 < v2):
                            clauses.append((-var_id(n, i, j, v1), -var_id(n, i, j + 1, v2)))
            elif rel == -1:
                for v1 in range(1, n + 1):
                    for v2 in range(1, n + 1):
                        if not (v1 > v2):
                            clauses.append((-var_id(n, i, j, v1), -var_id(n, i, j + 1, v2)))

    # Vertical inequalities (vcons[i][j] between (i,j) and (i+1,j))
    for i in range(n - 1):
        for j in range(n):
            rel = p.vcons[i][j]
            if rel == 1:
                for v1 in range(1, n + 1):
                    for v2 in range(1, n + 1):
                        if not (v1 < v2):
                            clauses.append((-var_id(n, i, j, v1), -var_id(n, i + 1, j, v2)))
            elif rel == -1:
                for v1 in range(1, n + 1):
                    for v2 in range(1, n + 1):
                        if not (v1 > v2):
                            clauses.append((-var_id(n, i, j, v1), -var_id(n, i + 1, j, v2)))

    return num_vars, clauses


def save_dimacs(path: str, num_vars: int, clauses: List[Clause]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"p cnf {num_vars} {len(clauses)}\n")
        for c in clauses:
            f.write(" ".join(str(x) for x in c) + " 0\n")


def assignment_satisfies_cnf(n: int, grid: List[List[int]], clauses: List[Clause]) -> bool:
    """Check a full grid satisfies all clauses (self-coded verifier)."""
    val: dict[int, int] = {}
    for i in range(n):
        for j in range(n):
            v = grid[i][j]
            for vv in range(1, n + 1):
                vid = var_id(n, i, j, vv)
                val[vid] = 1 if vv == v else -1
    for c in clauses:
        ok = False
        for lit in c:
            if lit > 0:
                if val.get(lit, -1) == 1:
                    ok = True
                    break
            else:
                if val.get(-lit, 1) == -1:
                    ok = True
                    break
        if not ok:
            return False
    return True
