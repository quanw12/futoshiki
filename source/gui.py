"""Minimal Tkinter UI: load puzzle file, pick algorithm, show solution and stats."""
from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from futoshiki_core import Puzzle, read_input, write_output  # noqa: E402
from solvers import solve  # noqa: E402


def grid_to_display(p: Puzzle, g: list[list[int]]) -> str:
    lines: list[str] = []
    for i in range(p.n):
        row: list[str] = []
        for j in range(p.n):
            row.append(str(g[i][j]))
            if j < p.n - 1:
                c = p.hcons[i][j]
                row.append("<" if c == 1 else ">" if c == -1 else " ")
        lines.append(" ".join(row))
        if i < p.n - 1:
            vr: list[str] = []
            for j in range(p.n):
                c = p.vcons[i][j]
                vr.append("v" if c == 1 else "^" if c == -1 else " ")
                if j < p.n - 1:
                    vr.append(" ")
            lines.append(" ".join(vr))
    return "\n".join(lines)


class FutoshikiApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Futoshiki solver")
        self.path_var = tk.StringVar(value="")
        self.algo_var = tk.StringVar(value="astar")
        self._build()

    def _build(self) -> None:
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill=tk.X)
        ttk.Button(top, text="Open puzzle…", command=self._browse).pack(side=tk.LEFT)
        ttk.Label(top, textvariable=self.path_var, wraplength=400).pack(
            side=tk.LEFT, padx=8, fill=tk.X, expand=True
        )

        mid = ttk.Frame(self.root, padding=8)
        mid.pack(fill=tk.X)
        ttk.Label(mid, text="Algorithm:").pack(side=tk.LEFT)
        ttk.Combobox(
            mid,
            textvariable=self.algo_var,
            values=["astar", "forward", "backward", "backtracking", "bruteforce"],
            state="readonly",
            width=14,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(mid, text="Solve", command=self._solve).pack(side=tk.LEFT, padx=8)

        stats = ttk.Frame(self.root, padding=(8, 0))
        stats.pack(fill=tk.X)
        self.stats_var = tk.StringVar(value="")
        ttk.Label(stats, textvariable=self.stats_var, font=("TkFixedFont", 9)).pack(anchor=tk.W)

        out = ttk.Frame(self.root, padding=8)
        out.pack(fill=tk.BOTH, expand=True)
        self.text = tk.Text(out, width=48, height=22, font=("Consolas", 11), wrap=tk.NONE)
        scroll = ttk.Scrollbar(out, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        save = ttk.Frame(self.root, padding=8)
        save.pack(fill=tk.X)
        ttk.Button(save, text="Save solution as…", command=self._save).pack(side=tk.LEFT)

        self._puzzle: Puzzle | None = None
        self._last_grid: list[list[int]] | None = None

    def _browse(self) -> None:
        fp = filedialog.askopenfilename(
            title="Select input-XX.txt",
            filetypes=[("Text", "*.txt"), ("All", "*.*")],
        )
        if fp:
            self.path_var.set(fp)
            try:
                self._puzzle = read_input(fp)
                self.text.delete("1.0", tk.END)
                self.text.insert(tk.END, f"Loaded n={self._puzzle.n}\n\n")
                self.stats_var.set("")
                self._last_grid = None
            except Exception as e:  # noqa: BLE001
                self._puzzle = None
                messagebox.showerror("Load error", str(e))

    def _solve(self) -> None:
        if self._puzzle is None:
            messagebox.showwarning("Solve", "Open a puzzle file first.")
            return
        algo = self.algo_var.get()
        r = solve(self._puzzle, algo)
        self.text.delete("1.0", tk.END)
        if r.solved_grid is None or r.contradiction:
            self._last_grid = None
            self.stats_var.set(
                f"No solution (contradiction={r.contradiction})  "
                f"time={r.runtime_sec:.6f}s  nodes={r.nodes_expanded}"
            )
            self.text.insert(tk.END, "No complete solution for this algorithm.\n")
            return
        self._last_grid = r.solved_grid
        self.stats_var.set(
            f"Solved with {algo}  time={r.runtime_sec:.6f}s  "
            f"nodes={r.nodes_expanded}  mem≈{r.memory_kb:.1f} KB"
        )
        self.text.insert(tk.END, grid_to_display(self._puzzle, r.solved_grid))

    def _save(self) -> None:
        if self._puzzle is None or self._last_grid is None:
            messagebox.showwarning("Save", "Solve successfully first.")
            return
        fp = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All", "*.*")],
        )
        if fp:
            write_output(fp, self._puzzle, self._last_grid)
            messagebox.showinfo("Saved", fp)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    FutoshikiApp().run()


if __name__ == "__main__":
    main()
