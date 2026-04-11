"""CLI for Futoshiki solvers (CSC14003 Project 2)."""
from __future__ import annotations

import argparse
import glob
import os
import sys

# Allow `python source/main.py` from repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from futoshiki_core import Puzzle, read_input, write_output  # noqa: E402
from ground_kb import build_ground_cnf_clauses, save_dimacs  # noqa: E402
from solvers import solve  # noqa: E402


def run_batch(indir: str, outdir: str, official_algo: str = "astar") -> None:
    """
    For each input-XX.txt:
    - Write outputs/output-XX.txt using `official_algo` (default: astar) when solved.
    - Also write per-algo files algo-output-XX.txt for benchmark algos.
    """
    files = sorted(glob.glob(os.path.join(indir, "input-*.txt")))
    algos = ["forward", "backward", "astar", "backtracking", "bruteforce"]
    print("file,algo,solved,time_sec,nodes,memory_kb")
    os.makedirs(outdir, exist_ok=True)
    for fp in files:
        p = read_input(fp)
        stem = os.path.basename(fp).replace("input", "output")
        official_written = False
        for algo in algos:
            r = solve(p, algo)
            solved = "1" if (r.solved_grid is not None and not r.contradiction) else "0"
            if solved == "1":
                write_output(os.path.join(outdir, f"{algo}-{stem}"), p, r.solved_grid)  # type: ignore[arg-type]
                if algo == official_algo and not official_written:
                    write_output(os.path.join(outdir, stem), p, r.solved_grid)  # type: ignore[arg-type]
                    official_written = True
            print(f"{os.path.basename(fp)},{algo},{solved},{r.runtime_sec:.6f},{r.nodes_expanded},{r.memory_kb:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, help="Path to one input file")
    parser.add_argument("--output", type=str, help="Path to output file")
    parser.add_argument(
        "--algo",
        type=str,
        default="astar",
        choices=["forward", "backward", "astar", "bruteforce", "backtracking"],
    )
    parser.add_argument("--batch", type=str, help="Input directory for batch mode")
    parser.add_argument("--outdir", type=str, default="outputs", help="Output directory in batch mode")
    parser.add_argument(
        "--export-dimacs",
        type=str,
        metavar="PATH",
        help="With --input: write grounded CNF in DIMACS format to PATH (verification).",
    )
    args = parser.parse_args()

    if args.batch:
        run_batch(args.batch, args.outdir)
        return

    if not args.input:
        raise SystemExit("Provide --input (single mode) or --batch (batch mode).")

    p = read_input(args.input)
    if args.export_dimacs:
        nvars, clauses = build_ground_cnf_clauses(p)
        save_dimacs(args.export_dimacs, nvars, clauses)
        print(f"Wrote DIMACS: {len(clauses)} clauses, {nvars} variables -> {args.export_dimacs}")

    r = solve(p, args.algo)
    if r.solved_grid is None or r.contradiction:
        print("No solution or contradiction detected.")
        return
    print(f"Solved with {args.algo}: time={r.runtime_sec:.6f}s nodes={r.nodes_expanded}")
    if args.output:
        od = os.path.dirname(args.output)
        if od:
            os.makedirs(od, exist_ok=True)
        write_output(args.output, p, r.solved_grid)


if __name__ == "__main__":
    main()
