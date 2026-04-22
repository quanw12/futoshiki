"""Validate output-01..10 against inputs_benchmark/input-01..10."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from futoshiki_core import is_valid_solution, read_input


def parse_grid(output_text: str, n: int) -> List[List[int]] | None:
    rows: List[List[int]] = []
    for line in output_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        nums = [int(x) for x in re.findall(r"\d+", line)]
        if len(nums) == n:
            rows.append(nums)
        if len(rows) == n:
            break
    return rows if len(rows) == n else None


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    inputs_dir = root / "inputs"
    outputs_dir = root / "outputs"

    ok_all = True
    for idx in range(1, 11):
        puzzle = read_input(str(inputs_dir / f"input-{idx:02d}.txt"))
        out_path = outputs_dir / f"output-{idx:02d}.txt"
        text = out_path.read_text(encoding="utf-8")
        grid = parse_grid(text, puzzle.n)
        valid = grid is not None and is_valid_solution(puzzle, grid)
        print(f"output-{idx:02d}: {'PASS' if valid else 'FAIL'}")
        ok_all = ok_all and valid

    if not ok_all:
        raise SystemExit(1)
    print("ALL_OUTPUTS_VALID")


if __name__ == "__main__":
    main()
