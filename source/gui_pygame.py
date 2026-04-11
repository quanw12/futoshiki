"""Futoshiki GUI with Pygame: mockup-style rounded grid, three columns, colored log."""
from __future__ import annotations

import os
import sys
from typing import List, Optional, Tuple

import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import filedialog, messagebox

from futoshiki_core import Puzzle, read_input, write_output  # noqa: E402
from solvers import solve  # noqa: E402

# --- Theme (dark mockup) ---
BG = (18, 18, 26)
PANEL = (30, 35, 48)
PANEL2 = (37, 43, 58)
BORDER = (61, 74, 99)
ACCENT_ORANGE = (249, 115, 22)
BLUE_CLUE = (37, 99, 235)
CELL_SOLVED = (226, 232, 240)
CELL_EMPTY = (45, 53, 72)
CONFLICT = (239, 68, 68)
TEXT = (241, 245, 249)
TEXT_MUTED = (148, 163, 184)
SYM_COLOR = (232, 236, 242)
LOG_BG = (15, 18, 25)
GREEN_OK = (74, 222, 128)
WARN = (251, 191, 36)
STEP_BORDER = (34, 211, 238)

Color = Tuple[int, int, int]

# Serif for grid numbers (assignment-style); sans for chrome. Fallback chain for Linux/macOS.
_SERIF = ("Times New Roman", "Georgia", "DejaVu Serif", "Liberation Serif", "Noto Serif")
_SANS_UI = ("Segoe UI", "Inter", "Roboto", "Ubuntu", "DejaVu Sans")


def _sys_font(families: Tuple[str, ...], size: int, bold: bool = False) -> pygame.font.Font:
    for name in families:
        f = pygame.font.SysFont(name, size, bold=bold)
        if f is not None:
            return f
    return pygame.font.SysFont("arial", size, bold=bold)


ALGOS: List[Tuple[str, str]] = [
    ("forward", "Forward chaining"),
    ("backward", "Backward chaining (SLD)"),
    ("astar", "A* search"),
    ("backtracking", "Backtracking"),
    ("bruteforce", "Brute force"),
]

_tk_root: Optional[tk.Tk] = None


def _tk() -> tk.Tk:
    global _tk_root
    if _tk_root is None:
        _tk_root = tk.Tk()
        _tk_root.withdraw()
    return _tk_root


def _panel(surf: pygame.Surface, rect: pygame.Rect, fill: Color, radius: int = 14) -> None:
    pygame.draw.rect(surf, fill, rect, border_radius=radius)
    pygame.draw.rect(surf, BORDER, rect, width=1, border_radius=radius)


class FutoshikiPygameApp:
    def __init__(self) -> None:
        pygame.init()
        self.w, self.h = 1280, 720
        self.screen = pygame.display.set_mode((self.w, self.h), pygame.RESIZABLE)
        pygame.display.set_caption("CSC14003 — Futoshiki Logic Solver")
        self.clock = pygame.time.Clock()

        self.font_title = _sys_font(_SANS_UI, 22, bold=True)
        self.font_ui = _sys_font(_SANS_UI, 15)
        self.font_small = _sys_font(_SANS_UI, 13)
        # Grid: serif like printed puzzles; slightly larger for readability.
        self.font_cell = _sys_font(_SERIF, 24, bold=True)
        self.font_log = _sys_font(("Consolas", "Cascadia Mono", "DejaVu Sans Mono"), 13)
        self._sym_fit: int = -1
        self._font_sym_fit: pygame.font.Font = _sys_font(_SERIF, 22, bold=True)

        self.puzzle: Optional[Puzzle] = None
        self.last_grid: Optional[List[List[int]]] = None
        self.display_grid: Optional[List[List[int]]] = None
        self.path_shown = ""
        self.algo = "astar"
        self.step_order: List[Tuple[int, int]] = []
        self.step_i = 0

        self.log_lines: List[Tuple[str, Color]] = []
        self.log_scroll = 0
        self.line_h = 18

        self.metric_cells = "—"
        self.metric_inf = "—"
        self.metric_time = "—"
        self.metric_nodes = "—"
        self.metric_valid = "—"

        self.radio_rects: List[Tuple[pygame.Rect, str]] = []
        self.btn_load: Optional[pygame.Rect] = None
        self.btn_solve: Optional[pygame.Rect] = None
        self.btn_step: Optional[pygame.Rect] = None
        self.btn_save: Optional[pygame.Rect] = None
        self.r_left = pygame.Rect(0, 0, 0, 0)
        self.r_mid = pygame.Rect(0, 0, 0, 0)
        self.r_right = pygame.Rect(0, 0, 0, 0)
        self.r_grid = pygame.Rect(0, 0, 0, 0)
        self.r_log = pygame.Rect(0, 0, 0, 0)
        self.r_metrics = pygame.Rect(0, 0, 0, 0)

        self.layout()

    def layout(self) -> None:
        pad = 14
        hdr = 48
        top = pad + hdr
        body_h = self.h - top - pad
        lw = max(380, int(self.w * 0.38))
        mw = max(220, int(self.w * 0.22))
        rw = self.w - lw - mw - 4 * pad
        if rw < 280:
            rw = max(280, self.w - lw - mw - 4 * pad)
        x = pad
        self.r_left = pygame.Rect(x, top, lw, body_h)
        x += lw + pad
        self.r_mid = pygame.Rect(x, top, mw, body_h)
        x += mw + pad
        self.r_right = pygame.Rect(x, top, max(200, rw), body_h)

        legend_h = 88
        self.r_grid = pygame.Rect(
            self.r_left.x + 10,
            self.r_left.y + 10,
            self.r_left.width - 20,
            self.r_left.height - 20 - legend_h,
        )

        # Align with draw_mid: header + puzzle size + "Select solver" block
        y = self.r_mid.y + 8 + 22 + 28 + 24
        self.radio_rects = []
        for val, _label in ALGOS:
            self.radio_rects.append((pygame.Rect(self.r_mid.x + 8, y, self.r_mid.width - 16, 26), val))
            y += 28
        y += 16
        bw = self.r_mid.width - 16
        self.btn_load = pygame.Rect(self.r_mid.x + 8, y, bw, 42)
        y += 50
        self.btn_solve = pygame.Rect(self.r_mid.x + 8, y, bw, 42)
        y += 50
        self.btn_step = pygame.Rect(self.r_mid.x + 8, y, bw, 42)

        metrics_h = 132
        self.r_metrics = pygame.Rect(
            self.r_right.x + 8,
            self.r_right.bottom - metrics_h - 44,
            self.r_right.width - 16,
            metrics_h,
        )
        log_top = self.r_right.y + 36
        log_h = self.r_metrics.y - log_top - 12
        if log_h < 100:
            self.r_metrics.y = min(self.r_right.bottom - 40, log_top + 100 + 12)
            log_h = max(80, self.r_metrics.y - log_top - 12)
        self.r_log = pygame.Rect(self.r_right.x + 8, log_top, self.r_right.width - 16, log_h)
        self.btn_save = pygame.Rect(self.r_right.x + 8, self.r_right.bottom - 36, 180, 30)

    def log(self, text: str, kind: str | None = None) -> None:
        if kind == "head":
            c = ACCENT_ORANGE
        elif kind == "ok":
            c = GREEN_OK
        elif kind == "warn":
            c = WARN
        else:
            c = TEXT
        self.log_lines.append((text, c))
        while len(self.log_lines) > 200:
            self.log_lines.pop(0)
        total_h = len(self.log_lines) * self.line_h + 8
        max_scroll = max(0, total_h - self.r_log.height)
        self.log_scroll = max_scroll

    def reset_metrics(self) -> None:
        self.metric_cells = "—"
        self.metric_inf = "—"
        self.metric_time = "—"
        self.metric_nodes = "—"
        self.metric_valid = "—"

    def load_file(self) -> None:
        fp = filedialog.askopenfilename(
            parent=_tk(),
            title="Select input-XX.txt",
            filetypes=[("Text", "*.txt"), ("All", "*.*")],
        )
        if not fp:
            return
        try:
            self.puzzle = read_input(fp)
            self.path_shown = fp
            self.last_grid = None
            self.display_grid = None
            self.step_order = []
            self.step_i = 0
            self.reset_metrics()
            self.log_lines = []
            self.log_scroll = 0
            self.log(f"Loaded puzzle n={self.puzzle.n}", "head")
            self.log(f"File: {fp}", None)
            assert self.puzzle is not None
            self.display_grid = [row[:] for row in self.puzzle.grid]
        except Exception as e:  # noqa: BLE001
            self.puzzle = None
            messagebox.showerror("Load error", str(e), parent=_tk())

    def do_solve(self) -> None:
        if self.puzzle is None:
            messagebox.showwarning("Solve", "Load an input file first.", parent=_tk())
            return
        self.log_lines = []
        self.log_scroll = 0
        self.log(f"Running solver: {self.algo} …", "head")
        r = solve(self.puzzle, self.algo)
        for line in r.messages:
            self.log(line, "ok" if "verified" in line.lower() else None)
        n = self.puzzle.n
        total = n * n
        if r.solved_grid is None or r.contradiction:
            self.last_grid = None
            self.display_grid = [row[:] for row in self.puzzle.grid]
            self.step_order = []
            self.step_i = 0
            filled = sum(1 for i in range(n) for j in range(n) if self.display_grid[i][j])
            self.metric_cells = f"{filled}/{total}"
            self.metric_inf = str(r.nodes_expanded)
            self.metric_time = f"{r.runtime_sec:.4f}s"
            self.metric_nodes = str(r.nodes_expanded)
            self.metric_valid = "NO"
            self.log("No complete grid to display.", "warn")
        else:
            self.last_grid = r.solved_grid
            self.display_grid = [row[:] for row in r.solved_grid]
            self.step_order = []
            self.step_i = 0
            self.metric_cells = f"{total}/{total} (Completed)"
            self.metric_inf = str(r.nodes_expanded)
            self.metric_time = f"{r.runtime_sec:.4f}s"
            self.metric_nodes = str(r.nodes_expanded)
            self.metric_valid = "YES"

    def do_step(self) -> None:
        if self.puzzle is None:
            messagebox.showwarning("Step", "Load a puzzle first.", parent=_tk())
            return
        if self.last_grid is None:
            messagebox.showinfo(
                "Step",
                "Solve the puzzle first, then use step-by-step to replay fills.",
                parent=_tk(),
            )
            return
        n = self.puzzle.n
        if not self.step_order:
            self.step_order = [(i, j) for i in range(n) for j in range(n) if self.puzzle.grid[i][j] == 0]
            self.step_i = 0
            self.display_grid = [row[:] for row in self.puzzle.grid]
            self.metric_valid = "In progress"
            self.log("Step-by-step: replay from givens; each click reveals one solved cell.", "head")
            if not self.step_order:
                self.log("No empty cells to reveal.", "warn")
                return

        if self.step_i >= len(self.step_order):
            self.log("Step-by-step: complete.", "ok")
            return
        i, j = self.step_order[self.step_i]
        assert self.display_grid is not None and self.last_grid is not None
        self.display_grid[i][j] = self.last_grid[i][j]
        self.step_i += 1
        filled = sum(1 for ii in range(n) for jj in range(n) if self.display_grid[ii][jj] != 0)
        done = filled >= n * n
        self.metric_cells = f"{filled}/{n * n}" + (" (Completed)" if done else "")
        self.metric_valid = "YES" if done else "In progress"
        self.log(f"Revealed cell ({i + 1},{j + 1}) = {self.last_grid[i][j]}", None)

    def do_save(self) -> None:
        if self.puzzle is None or self.last_grid is None:
            messagebox.showwarning("Save", "Solve successfully first.", parent=_tk())
            return
        fp = filedialog.asksaveasfilename(
            parent=_tk(),
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All", "*.*")],
        )
        if fp:
            write_output(fp, self.puzzle, self.last_grid)
            messagebox.showinfo("Saved", fp, parent=_tk())

    def _cell_colors(self, i: int, j: int) -> Tuple[Color, Color]:
        assert self.puzzle is not None and self.display_grid is not None
        p, g = self.puzzle, self.display_grid
        v = g[i][j]
        if v == 0:
            return CELL_EMPTY, TEXT_MUTED
        if p.grid[i][j] != 0:
            return BLUE_CLUE, (255, 255, 255)
        if self.last_grid is not None and v != self.last_grid[i][j]:
            return CONFLICT, (255, 255, 255)
        return CELL_SOLVED, (15, 23, 42)

    def draw_grid(self) -> None:
        if self.puzzle is None or self.display_grid is None:
            t = self.font_ui.render("Load an input file to show the grid.", True, TEXT_MUTED)
            self.screen.blit(t, t.get_rect(center=self.r_grid.center))
            return

        p, g = self.puzzle, self.display_grid
        n = p.n
        rw, rh = self.r_grid.width, self.r_grid.height
        gap_h = max(20, min(32, rw // max(6, n * 3)))
        gap_v = max(18, min(30, rh // max(6, n * 3)))
        cell = max(26, min(56, min((rw - (n - 1) * gap_h) // n, (rh - (n - 1) * gap_v) // n)))
        sym_size = max(18, min(30, (cell + gap_h) // 2))
        if sym_size != self._sym_fit:
            self._sym_fit = sym_size
            self._font_sym_fit = _sys_font(_SERIF, sym_size, bold=True)
        sym_font = self._font_sym_fit
        row_w = n * cell + (n - 1) * gap_h
        col_h = n * cell + (n - 1) * gap_v
        ox = self.r_grid.x + (rw - row_w) // 2
        oy = self.r_grid.y + (rh - col_h) // 2
        rad = max(6, min(12, cell // 4))

        for i in range(n):
            y0 = oy + i * (cell + gap_v)
            x = ox
            for j in range(n):
                if j > 0:
                    sh = p.hcons[i][j - 1]
                    sym = "<" if sh == 1 else ">" if sh == -1 else ""
                    if sym:
                        s = sym_font.render(sym, True, SYM_COLOR)
                        self.screen.blit(s, s.get_rect(center=(x + gap_h // 2, y0 + cell // 2)))
                    x += gap_h
                fill, tcol = self._cell_colors(i, j)
                r = pygame.Rect(x, y0, cell, cell)
                pygame.draw.rect(self.screen, fill, r, border_radius=rad)
                pygame.draw.rect(self.screen, BORDER, r, width=1, border_radius=rad)
                if g[i][j] == 0:
                    dash = self.font_cell.render("-", True, tcol)
                    self.screen.blit(dash, dash.get_rect(center=r.center))
                else:
                    num = self.font_cell.render(str(g[i][j]), True, tcol)
                    self.screen.blit(num, num.get_rect(center=r.center))
                x += cell
            if i < n - 1:
                y_mid = y0 + cell + gap_v // 2
                for j in range(n):
                    x_left = ox + j * (cell + gap_h)
                    sv = p.vcons[i][j]
                    # 1 = top < bottom → ∧ (wedge up); -1 = top > bottom → ∨ (vee down)
                    sym = "\u2227" if sv == 1 else "\u2228" if sv == -1 else ""
                    if sym:
                        s = sym_font.render(sym, True, SYM_COLOR)
                        self.screen.blit(s, s.get_rect(center=(x_left + cell // 2, y_mid)))

        # Legend bottom-right inside left panel
        lx = self.r_left.right - 210
        ly = self.r_left.bottom - 78
        for i, (col, label) in enumerate(
            [
                (BLUE_CLUE, "Given clue"),
                (CELL_SOLVED, "Solved cell"),
                (CONFLICT, "Conflict"),
            ]
        ):
            yy = ly + i * 22
            rr = pygame.Rect(lx, yy, 16, 16)
            pygame.draw.rect(self.screen, col, rr, border_radius=4)
            pygame.draw.rect(self.screen, BORDER, rr, width=1, border_radius=4)
            self.screen.blit(self.font_small.render(label, True, TEXT), (lx + 22, yy - 1))

    def draw_mid(self) -> None:
        y = self.r_mid.y + 8
        self.screen.blit(self.font_ui.render("Puzzle size", True, TEXT_MUTED), (self.r_mid.x + 8, y))
        y += 22
        sz = f"{self.puzzle.n}×{self.puzzle.n}" if self.puzzle else "—"
        self.screen.blit(self.font_small.render(sz, True, TEXT), (self.r_mid.x + 8, y))
        y += 28
        self.screen.blit(self.font_ui.render("Select solver", True, TEXT_MUTED), (self.r_mid.x + 8, y))
        y += 24
        for (rect, val), (_, label) in zip(self.radio_rects, ALGOS):
            sel = val == self.algo
            if sel:
                pygame.draw.rect(self.screen, ACCENT_ORANGE, rect, border_radius=8)
            else:
                pygame.draw.rect(self.screen, PANEL2, rect, border_radius=8)
            self.screen.blit(
                self.font_small.render(label, True, (255, 255, 255) if sel else TEXT),
                (rect.x + 8, rect.y + 5),
            )

        def draw_btn(rect: pygame.Rect, text: str, bg: Color, outline: Optional[Color] = None) -> None:
            if outline:
                pygame.draw.rect(self.screen, outline, rect.inflate(4, 4), border_radius=10)
            pygame.draw.rect(self.screen, bg, rect, border_radius=8)
            pygame.draw.rect(self.screen, BORDER, rect, width=1, border_radius=8)
            surf = self.font_ui.render(text, True, TEXT if bg == (71, 85, 105) else (255, 255, 255))
            self.screen.blit(surf, surf.get_rect(center=rect.center))

        if self.btn_load:
            draw_btn(self.btn_load, "LOAD INPUT FILE", (59, 130, 246))
        if self.btn_solve:
            draw_btn(self.btn_solve, "SOLVE PUZZLE", ACCENT_ORANGE)
        if self.btn_step:
            draw_btn(self.btn_step, "STEP-BY-STEP", (71, 85, 105), STEP_BORDER)

        if self.path_shown:
            path = self.path_shown if len(self.path_shown) < 42 else "…" + self.path_shown[-40:]
            self.screen.blit(self.font_small.render(path, True, TEXT_MUTED), (self.r_mid.x + 8, self.r_mid.bottom - 52))

    def draw_right(self) -> None:
        self.screen.blit(self.font_ui.render("Algorithm details", True, TEXT_MUTED), (self.r_right.x + 8, self.r_right.y + 8))

        pygame.draw.rect(self.screen, LOG_BG, self.r_log, border_radius=10)
        pygame.draw.rect(self.screen, BORDER, self.r_log, width=1, border_radius=10)

        prev = self.screen.get_clip()
        self.screen.set_clip(self.r_log.inflate(-2, -2))
        y = self.r_log.y + 6 - self.log_scroll
        for line, col in self.log_lines:
            if y + self.line_h > self.r_log.y and y < self.r_log.bottom:
                self.screen.blit(self.font_log.render(line, True, col), (self.r_log.x + 8, y))
            y += self.line_h
        self.screen.set_clip(prev)

        _panel(self.screen, self.r_metrics, PANEL2, 10)
        mx, my = self.r_metrics.x + 10, self.r_metrics.y + 8
        rows = [
            ("Total cells assigned", self.metric_cells),
            ("Propagation / search steps", self.metric_inf),
            ("Execution time", self.metric_time),
            ("Nodes expanded", self.metric_nodes),
            ("Solution valid", self.metric_valid),
        ]
        for title, val in rows:
            self.screen.blit(self.font_small.render(title + ":", True, TEXT_MUTED), (mx, my))
            if title == "Solution valid":
                if val == "YES":
                    vc = GREEN_OK
                elif val in ("NO",):
                    vc = CONFLICT
                elif val == "In progress":
                    vc = WARN
                else:
                    vc = TEXT_MUTED
            else:
                vc = TEXT
            self.screen.blit(self.font_small.render(val, True, vc), (mx + 200, my))
            my += 24

        if self.btn_save:
            pygame.draw.rect(self.screen, (51, 65, 85), self.btn_save, border_radius=6)
            self.screen.blit(
                self.font_small.render("Save solution as…", True, TEXT),
                (self.btn_save.x + 10, self.btn_save.y + 7),
            )

    def on_click(self, pos: Tuple[int, int]) -> None:
        for rect, val in self.radio_rects:
            if rect.collidepoint(pos):
                self.algo = val
                return
        if self.btn_load and self.btn_load.collidepoint(pos):
            self.load_file()
            return
        if self.btn_solve and self.btn_solve.collidepoint(pos):
            self.do_solve()
            return
        if self.btn_step and self.btn_step.inflate(8, 8).collidepoint(pos):
            self.do_step()
            return
        if self.btn_save and self.btn_save.collidepoint(pos):
            self.do_save()

    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.w, self.h = max(960, event.w), max(620, event.h)
                    self.screen = pygame.display.set_mode((self.w, self.h), pygame.RESIZABLE)
                    self.layout()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.on_click(event.pos)
                elif event.type == pygame.MOUSEWHEEL:
                    if self.r_log.collidepoint(pygame.mouse.get_pos()):
                        total_h = len(self.log_lines) * self.line_h + 8
                        max_s = max(0, total_h - self.r_log.height)
                        self.log_scroll = max(0, min(max_s, self.log_scroll - event.y * 24))

            self.screen.fill(BG)
            title = self.font_title.render("CSC14003 AI Project — Futoshiki Logic Solver", True, TEXT)
            self.screen.blit(title, (14, 14))

            _panel(self.screen, self.r_left, PANEL)
            _panel(self.screen, self.r_mid, PANEL2)
            _panel(self.screen, self.r_right, PANEL)

            self.draw_grid()
            self.draw_mid()
            self.draw_right()

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()


def main() -> None:
    FutoshikiPygameApp().run()


if __name__ == "__main__":
    main()
