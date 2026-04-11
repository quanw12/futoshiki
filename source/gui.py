"""Futoshiki desktop UI: dark theme, canvas grid, algorithm choice, diagnostics log."""
from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from futoshiki_core import Puzzle, read_input, write_output  # noqa: E402
from solvers import solve  # noqa: E402

# --- Theme (approximates assignment mockup: navy + blue + orange) ---
BG = "#161922"
PANEL = "#1e2330"
PANEL2 = "#252b3a"
ACCENT = "#f97316"
ACCENT_DIM = "#ea580c"
BLUE_CLUE = "#2563eb"
CELL_SOLVED = "#e2e8f0"
CELL_EMPTY = "#2d3548"
TEXT = "#f1f5f9"
TEXT_MUTED = "#94a3b8"
GRID_LINE = "#3d4a63"
LOG_BG = "#0f1219"
GREEN_OK = "#4ade80"


class FutoshikiApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("CSC14003 — Futoshiki Logic Solver")
        self.root.configure(bg=BG)
        self.root.minsize(1100, 640)

        self.path_var = tk.StringVar(value="")
        self.algo_var = tk.StringVar(value="astar")
        self._puzzle: Puzzle | None = None
        self._last_grid: list[list[int]] | None = None
        self._display_grid: list[list[int]] | None = None
        self._step_order: list[tuple[int, int]] = []
        self._step_i = 0

        self._font_title = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        self._font_ui = tkfont.Font(family="Segoe UI", size=10)
        self._font_cell = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        self._font_small = tkfont.Font(family="Segoe UI", size=9)
        self._font_log = tkfont.Font(family="Consolas", size=10)

        self._build()
        self.root.bind("<Configure>", self._on_resize)

    def _build(self) -> None:
        outer = tk.Frame(self.root, bg=BG, padx=14, pady=12)
        outer.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            outer,
            text="CSC14003 AI Project — Futoshiki Logic Solver",
            font=self._font_title,
            fg=TEXT,
            bg=BG,
        ).pack(anchor=tk.W, pady=(0, 10))

        body = tk.Frame(outer, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, weight=2)
        body.rowconfigure(0, weight=1)

        # --- Left: puzzle canvas + legend ---
        left = tk.Frame(body, bg=PANEL, padx=12, pady=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.canvas = tk.Canvas(
            left,
            bg=PANEL,
            highlightthickness=1,
            highlightbackground=GRID_LINE,
            width=420,
            height=420,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        leg = tk.Frame(left, bg=PANEL)
        leg.pack(fill=tk.X, pady=(10, 0))
        self._legend_row(leg, BLUE_CLUE, "Given clue")
        self._legend_row(leg, CELL_SOLVED, "Solved cell", fg="#0f172a")
        self._legend_row(leg, "#ef4444", "Conflict (invalid partial)")

        # --- Middle: controls ---
        mid = tk.Frame(body, bg=PANEL2, padx=16, pady=16)
        mid.grid(row=0, column=1, sticky="nsew", padx=4)
        tk.Label(mid, text="Puzzle", font=self._font_ui, fg=TEXT_MUTED, bg=PANEL2).pack(anchor=tk.W)
        path_row = tk.Frame(mid, bg=PANEL2)
        path_row.pack(fill=tk.X, pady=(2, 12))
        tk.Label(
            path_row,
            textvariable=self.path_var,
            font=self._font_small,
            fg=TEXT,
            bg=PANEL2,
            wraplength=220,
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

        tk.Label(mid, text="Select solver", font=self._font_ui, fg=TEXT_MUTED, bg=PANEL2).pack(anchor=tk.W)
        algos = [
            ("forward", "Forward chaining"),
            ("backward", "Backward chaining (SLD)"),
            ("astar", "A* search"),
            ("backtracking", "Backtracking"),
            ("bruteforce", "Brute force"),
        ]
        for val, label in algos:
            tk.Radiobutton(
                mid,
                text=label,
                variable=self.algo_var,
                value=val,
                font=self._font_small,
                fg=TEXT,
                bg=PANEL2,
                selectcolor=PANEL,
                activebackground=PANEL2,
                activeforeground=TEXT,
                anchor=tk.W,
            ).pack(fill=tk.X, pady=2)

        tk.Frame(mid, bg=PANEL2, height=12).pack()

        self._btn(
            mid,
            "LOAD INPUT FILE",
            self._browse,
            ACCENT,
            hover=ACCENT_DIM,
        )
        self._btn(mid, "SOLVE PUZZLE", self._solve, "#3b82f6", "#2563eb")
        self._btn(mid, "STEP-BY-STEP", self._step, "#475569", "#334155")

        # --- Right: log + metrics ---
        right = tk.Frame(body, bg=PANEL, padx=10, pady=10)
        right.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        right.rowconfigure(1, weight=1)
        tk.Label(
            right,
            text="Algorithm details",
            font=self._font_ui,
            fg=TEXT_MUTED,
            bg=PANEL,
        ).grid(row=0, column=0, sticky=tk.W)

        log_frame = tk.Frame(right, bg=LOG_BG, highlightthickness=1, highlightbackground=GRID_LINE)
        log_frame.grid(row=1, column=0, sticky="nsew", pady=(4, 8))
        right.columnconfigure(0, weight=1)
        self.log = tk.Text(
            log_frame,
            wrap=tk.WORD,
            font=self._font_log,
            bg=LOG_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            padx=8,
            pady=8,
        )
        sb = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.log.tag_configure("head", foreground=ACCENT)
        self.log.tag_configure("ok", foreground=GREEN_OK)
        self.log.tag_configure("warn", foreground="#fbbf24")

        met = tk.Frame(right, bg=PANEL2, padx=10, pady=10)
        met.grid(row=2, column=0, sticky="ew")
        self.metric_cells = tk.StringVar(value="—")
        self.metric_inf = tk.StringVar(value="—")
        self.metric_time = tk.StringVar(value="—")
        self.metric_nodes = tk.StringVar(value="—")
        self._metric_line(met, "Total cells assigned", self.metric_cells)
        self._metric_line(met, "Propagation / search steps", self.metric_inf)
        self._metric_line(met, "Execution time", self.metric_time)
        self._metric_line(met, "Nodes expanded", self.metric_nodes)

        save_row = tk.Frame(right, bg=PANEL)
        save_row.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        tk.Button(
            save_row,
            text="Save solution as…",
            command=self._save,
            font=self._font_small,
            bg="#334155",
            fg=TEXT,
            activebackground="#475569",
            activeforeground=TEXT,
            relief=tk.FLAT,
            padx=12,
            pady=6,
        ).pack(side=tk.LEFT)

    def _legend_row(self, parent: tk.Frame, color: str, text: str, fg: str | None = None) -> None:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill=tk.X, pady=2)
        sw = tk.Canvas(row, width=18, height=18, bg=PANEL, highlightthickness=0)
        sw.pack(side=tk.LEFT, padx=(0, 8))
        sw.create_rectangle(2, 2, 16, 16, fill=color, outline=GRID_LINE)
        tk.Label(
            row,
            text=text,
            font=self._font_small,
            fg=fg or TEXT,
            bg=PANEL,
        ).pack(side=tk.LEFT)

    def _metric_line(self, parent: tk.Frame, title: str, var: tk.StringVar) -> None:
        f = tk.Frame(parent, bg=PANEL2)
        f.pack(fill=tk.X, pady=3)
        tk.Label(f, text=title + ":", font=self._font_small, fg=TEXT_MUTED, bg=PANEL2, width=26, anchor=tk.W).pack(
            side=tk.LEFT
        )
        tk.Label(f, textvariable=var, font=self._font_small, fg=TEXT, bg=PANEL2, anchor=tk.W).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

    def _btn(self, parent: tk.Frame, text: str, cmd, bg: str, hover: str) -> None:
        b = tk.Button(
            parent,
            text=text,
            command=cmd,
            font=self._font_ui,
            bg=bg,
            fg="#ffffff" if bg != "#475569" else TEXT,
            activebackground=hover,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=10,
            cursor="hand2",
        )
        b.pack(fill=tk.X, pady=6)

    def _log(self, line: str, tag: str | None = None) -> None:
        self.log.insert(tk.END, line + "\n", tag or ())
        self.log.see(tk.END)

    def _browse(self) -> None:
        fp = filedialog.askopenfilename(
            title="Select input-XX.txt",
            filetypes=[("Text", "*.txt"), ("All", "*.*")],
        )
        if not fp:
            return
        self.path_var.set(fp)
        try:
            self._puzzle = read_input(fp)
            self._last_grid = None
            self._display_grid = None
            self._step_order = []
            self._step_i = 0
            self._reset_metrics()
            self.log.delete("1.0", tk.END)
            self._log(f"Loaded puzzle n={self._puzzle.n}", "head")
            self._log(f"File: {fp}", None)
            self._display_grid = [row[:] for row in self._puzzle.grid]
            self._draw_grid()
        except Exception as e:  # noqa: BLE001
            self._puzzle = None
            messagebox.showerror("Load error", str(e))

    def _reset_metrics(self) -> None:
        self.metric_cells.set("—")
        self.metric_inf.set("—")
        self.metric_time.set("—")
        self.metric_nodes.set("—")

    def _solve(self) -> None:
        if self._puzzle is None:
            messagebox.showwarning("Solve", "Load an input file first.")
            return
        algo = self.algo_var.get()
        self.log.delete("1.0", tk.END)
        self._log(f"Running solver: {algo} …", "head")
        self.root.update_idletasks()
        r = solve(self._puzzle, algo)
        for line in r.messages:
            self._log(line, "ok" if "verified" in line.lower() else None)
        n = self._puzzle.n
        total = n * n
        if r.solved_grid is None or r.contradiction:
            self._last_grid = None
            self._display_grid = [row[:] for row in self._puzzle.grid]
            self._step_order = []
            self._step_i = 0
            self.metric_cells.set(f"{sum(1 for i in range(n) for j in range(n) if self._display_grid[i][j])}/{total}")
            self.metric_inf.set(str(r.nodes_expanded))
            self.metric_time.set(f"{r.runtime_sec:.4f}s")
            self.metric_nodes.set(str(r.nodes_expanded))
            self._log("No complete grid to display.", "warn")
        else:
            self._last_grid = r.solved_grid
            self._display_grid = [row[:] for row in r.solved_grid]
            self._step_order = []
            self._step_i = 0
            self.metric_cells.set(f"{total}/{total}")
            self.metric_inf.set(str(r.nodes_expanded))
            self.metric_time.set(f"{r.runtime_sec:.4f}s")
            self.metric_nodes.set(str(r.nodes_expanded))
        self._draw_grid()

    def _step(self) -> None:
        """Reveal solved cells one at a time (row-major over previously empty cells)."""
        if self._puzzle is None:
            messagebox.showwarning("Step", "Load a puzzle first.")
            return
        if self._last_grid is None:
            messagebox.showinfo("Step", "Solve the puzzle first, then use step-by-step to replay fills.")
            return
        p = self._puzzle
        n = p.n
        if not self._step_order:
            order = [(i, j) for i in range(n) for j in range(n) if p.grid[i][j] == 0]
            self._step_order = order
            self._step_i = 0
            self._display_grid = [row[:] for row in p.grid]
            self._draw_grid()
            self._log("Step-by-step: replay from givens; each click reveals one solved cell.", "head")
            if not self._step_order:
                self._log("No empty cells to reveal.", "warn")
                return

        if self._step_i >= len(self._step_order):
            self._log("Step-by-step: complete.", "ok")
            return
        i, j = self._step_order[self._step_i]
        self._display_grid[i][j] = self._last_grid[i][j]
        self._step_i += 1
        filled = sum(1 for ii in range(n) for jj in range(n) if self._display_grid[ii][jj] != 0)
        self.metric_cells.set(f"{filled}/{n * n}")
        self._log(f"Revealed cell ({i + 1},{j + 1}) = {self._last_grid[i][j]}", None)
        self._draw_grid()

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

    def _on_resize(self, _evt: tk.Event) -> None:
        if self._puzzle is not None and self._display_grid is not None:
            self._draw_grid()

    def _cell_style(self, i: int, j: int) -> tuple[str, str]:
        """Return fill, text color for cell (i,j)."""
        assert self._puzzle is not None and self._display_grid is not None
        p = self._puzzle
        g = self._display_grid
        v = g[i][j]
        if v == 0:
            return CELL_EMPTY, TEXT_MUTED
        if p.grid[i][j] != 0:
            return BLUE_CLUE, "#ffffff"
        return CELL_SOLVED, "#0f172a"

    def _draw_grid(self) -> None:
        self.canvas.delete("all")
        if self._puzzle is None or self._display_grid is None:
            w = int(self.canvas.winfo_width() or 400)
            h = int(self.canvas.winfo_height() or 400)
            self.canvas.create_text(
                w // 2,
                h // 2,
                text="Load an input file to show the grid.",
                fill=TEXT_MUTED,
                font=self._font_ui,
            )
            return

        p = self._puzzle
        g = self._display_grid
        n = p.n
        cw = int(self.canvas.winfo_width() or 400)
        ch = int(self.canvas.winfo_height() or 400)
        gap_h = 20
        gap_v = 18
        cell_w_budget = (cw - 48 - (n - 1) * gap_h) // max(1, n)
        cell_h_budget = (ch - 48 - (n - 1) * gap_v) // max(1, n)
        cell = max(26, min(56, min(cell_w_budget, cell_h_budget)))
        gap_h = max(16, min(28, cell // 2 + 4))
        gap_v = max(14, min(26, cell // 2 + 2))
        row_w = n * cell + (n - 1) * gap_h
        col_h = n * cell + (n - 1) * gap_v
        ox = max(8, (cw - row_w) // 2)
        oy = max(8, (ch - col_h) // 2)

        for i in range(n):
            y0 = oy + i * (cell + gap_v)
            x = ox
            for j in range(n):
                if j > 0:
                    sh = p.hcons[i][j - 1]
                    sym = "<" if sh == 1 else ">" if sh == -1 else ""
                    if sym:
                        self.canvas.create_text(
                            x + gap_h // 2,
                            y0 + cell // 2,
                            text=sym,
                            fill=ACCENT,
                            font=self._font_cell,
                        )
                    x += gap_h
                fill, tcol = self._cell_style(i, j)
                self.canvas.create_rectangle(
                    x, y0, x + cell, y0 + cell, fill=fill, outline=GRID_LINE, width=1
                )
                if g[i][j] != 0:
                    self.canvas.create_text(
                        x + cell // 2,
                        y0 + cell // 2,
                        text=str(g[i][j]),
                        fill=tcol,
                        font=self._font_cell,
                    )
                x += cell
            if i < n - 1:
                y_mid = y0 + cell + gap_v // 2
                for j in range(n):
                    x_left = ox + j * (cell + gap_h)
                    sv = p.vcons[i][j]
                    sym = "v" if sv == 1 else "^" if sv == -1 else ""
                    if sym:
                        self.canvas.create_text(
                            x_left + cell // 2,
                            y_mid,
                            text=sym,
                            fill=ACCENT,
                            font=self._font_ui,
                        )

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    FutoshikiApp().run()


if __name__ == "__main__":
    main()
