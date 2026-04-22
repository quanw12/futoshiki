"""Ground Futoshiki FOL constraints into CNF and export DIMACS."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from futoshiki_core import Puzzle, read_input

CellValue = Tuple[int, int, int]


@dataclass
class GroundKB:
    n_vars: int
    clauses: List[List[int]]
    atom_to_var: Dict[CellValue, int]
    var_to_atom: Dict[int, CellValue]


def _build_atom_index(n: int) -> tuple[Dict[CellValue, int], Dict[int, CellValue]]:
    atom_to_var: Dict[CellValue, int] = {}
    var_to_atom: Dict[int, CellValue] = {}
    vid = 1
    for i in range(n):
        for j in range(n):
            for v in range(1, n + 1):
                key = (i, j, v)
                atom_to_var[key] = vid
                var_to_atom[vid] = key
                vid += 1
    return atom_to_var, var_to_atom


def _var(atom_to_var: Dict[CellValue, int], i: int, j: int, v: int) -> int:
    return atom_to_var[(i, j, v)]


def _exactly_one_value_per_cell(p: Puzzle, atom_to_var: Dict[CellValue, int], clauses: List[List[int]]) -> None:
    n = p.n
    for i in range(n):
        for j in range(n):
            # At least one value.
            clauses.append([_var(atom_to_var, i, j, v) for v in range(1, n + 1)])
            # At most one value.
            for v1 in range(1, n + 1):
                for v2 in range(v1 + 1, n + 1):
                    clauses.append([-_var(atom_to_var, i, j, v1), -_var(atom_to_var, i, j, v2)])


def _row_uniqueness(p: Puzzle, atom_to_var: Dict[CellValue, int], clauses: List[List[int]]) -> None:
    n = p.n
    for i in range(n):
        for v in range(1, n + 1):
            for j1 in range(n):
                for j2 in range(j1 + 1, n):
                    clauses.append([-_var(atom_to_var, i, j1, v), -_var(atom_to_var, i, j2, v)])


def _col_uniqueness(p: Puzzle, atom_to_var: Dict[CellValue, int], clauses: List[List[int]]) -> None:
    n = p.n
    for j in range(n):
        for v in range(1, n + 1):
            for i1 in range(n):
                for i2 in range(i1 + 1, n):
                    clauses.append([-_var(atom_to_var, i1, j, v), -_var(atom_to_var, i2, j, v)])


def _given_clues(p: Puzzle, atom_to_var: Dict[CellValue, int], clauses: List[List[int]]) -> None:
    n = p.n
    for i in range(n):
        for j in range(n):
            g = p.grid[i][j]
            if g != 0:
                clauses.append([_var(atom_to_var, i, j, g)])


def _horizontal_inequalities(p: Puzzle, atom_to_var: Dict[CellValue, int], clauses: List[List[int]]) -> None:
    n = p.n
    for i in range(n):
        for j in range(n - 1):
            rel = p.hcons[i][j]
            if rel == 0:
                continue
            for left in range(1, n + 1):
                for right in range(1, n + 1):
                    ok = (left < right) if rel == 1 else (left > right)
                    if not ok:
                        clauses.append([-_var(atom_to_var, i, j, left), -_var(atom_to_var, i, j + 1, right)])


def _vertical_inequalities(p: Puzzle, atom_to_var: Dict[CellValue, int], clauses: List[List[int]]) -> None:
    n = p.n
    for i in range(n - 1):
        for j in range(n):
            rel = p.vcons[i][j]
            if rel == 0:
                continue
            for top in range(1, n + 1):
                for bottom in range(1, n + 1):
                    ok = (top < bottom) if rel == 1 else (top > bottom)
                    if not ok:
                        clauses.append([-_var(atom_to_var, i, j, top), -_var(atom_to_var, i + 1, j, bottom)])


def ground_kb_to_cnf(p: Puzzle) -> GroundKB:
    atom_to_var, var_to_atom = _build_atom_index(p.n)
    clauses: List[List[int]] = []
    _exactly_one_value_per_cell(p, atom_to_var, clauses)
    _row_uniqueness(p, atom_to_var, clauses)
    _col_uniqueness(p, atom_to_var, clauses)
    _given_clues(p, atom_to_var, clauses)
    _horizontal_inequalities(p, atom_to_var, clauses)
    _vertical_inequalities(p, atom_to_var, clauses)
    return GroundKB(len(atom_to_var), clauses, atom_to_var, var_to_atom)


def write_dimacs(path: str | Path, kb: GroundKB) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        f.write(f"p cnf {kb.n_vars} {len(kb.clauses)}\n")
        for clause in kb.clauses:
            f.write(" ".join(str(lit) for lit in clause) + " 0\n")


def generate_dimacs_from_input(input_path: str | Path, output_path: str | Path) -> GroundKB:
    puzzle = read_input(str(input_path))
    kb = ground_kb_to_cnf(puzzle)
    write_dimacs(output_path, kb)
    return kb


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate grounded CNF (DIMACS) for a Futoshiki input file.")
    parser.add_argument("input_file", help="Path to input-XX.txt")
    parser.add_argument("output_dimacs", help="Path to output .cnf/.dimacs file")
    args = parser.parse_args()

    generated = generate_dimacs_from_input(args.input_file, args.output_dimacs)
    print(f"Generated {len(generated.clauses)} clauses, {generated.n_vars} vars -> {args.output_dimacs}")
