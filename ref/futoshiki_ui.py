"""
Futoshiki Solver — UI/UX Application
Giao diện trực quan: từng bước giải + biểu đồ so sánh thuật toán
Yêu cầu: Python 3.8+, tkinter (có sẵn), matplotlib
Cài matplotlib nếu chưa có: pip install matplotlib
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import tracemalloc
import copy
import heapq
import itertools
import os
import glob
from collections import defaultdict

# ─── Matplotlib embed ────────────────────────────────────────────────────────
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import FancyBboxPatch
import matplotlib.ticker as ticker
import numpy as np

# ═══════════════════════════════════════════════════════════════════════════════
# THEME & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

THEME = {
    "bg":          "#0F1117",
    "surface":     "#1A1D27",
    "surface2":    "#232738",
    "surface3":    "#2D3147",
    "accent":      "#6C8EFF",
    "accent2":     "#A78BFA",
    "green":       "#34D399",
    "yellow":      "#FBBF24",
    "red":         "#F87171",
    "text":        "#F1F5F9",
    "text_muted":  "#94A3B8",
    "text_dim":    "#4A5568",
    "border":      "#2D3147",
    "bt_color":    "#F87171",
    "fc_color":    "#FBBF24",
    "bc_color":    "#A78BFA",
    "as_color":    "#34D399",
}

ALGO_COLORS = {
    "BT":  THEME["bt_color"],
    "FC":  THEME["fc_color"],
    "BC":  THEME["bc_color"],
    "A*":  THEME["as_color"],
}

FONT_TITLE  = ("Consolas", 22, "bold")
FONT_HEAD   = ("Consolas", 13, "bold")
FONT_BODY   = ("Consolas", 11)
FONT_MONO   = ("Courier New", 10)
FONT_CELL   = ("Consolas", 18, "bold")
FONT_SMALL  = ("Consolas", 9)

# ═══════════════════════════════════════════════════════════════════════════════
# BACKEND — ĐỌC FILE & THUẬT TOÁN
# ═══════════════════════════════════════════════════════════════════════════════

def read_futoshiki_input(file_path):
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    N = int(lines[0])
    cur = 1
    grid = []
    for _ in range(N):
        grid.append(list(map(int, lines[cur].split(',')))); cur += 1
    horiz = []
    for _ in range(N):
        horiz.append(list(map(int, lines[cur].split(',')))); cur += 1
    vert = []
    for _ in range(N - 1):
        vert.append(list(map(int, lines[cur].split(',')))); cur += 1
    return N, grid, horiz, vert

def is_safe(grid, row, col, num, N, horiz, vert):
    for j in range(N):
        if grid[row][j] == num: return False
    for i in range(N):
        if grid[i][col] == num: return False
    if col > 0 and grid[row][col-1] != 0:
        if horiz[row][col-1] == 1 and not (grid[row][col-1] < num): return False
        if horiz[row][col-1] == -1 and not (grid[row][col-1] > num): return False
    if col < N-1 and grid[row][col+1] != 0:
        if horiz[row][col] == 1 and not (num < grid[row][col+1]): return False
        if horiz[row][col] == -1 and not (num > grid[row][col+1]): return False
    if row > 0 and grid[row-1][col] != 0:
        if vert[row-1][col] == 1 and not (grid[row-1][col] < num): return False
        if vert[row-1][col] == -1 and not (grid[row-1][col] > num): return False
    if row < N-1 and grid[row+1][col] != 0:
        if vert[row][col] == 1 and not (num < grid[row+1][col]): return False
        if vert[row][col] == -1 and not (num > grid[row+1][col]): return False
    return True

def find_empty(grid, N):
    for i in range(N):
        for j in range(N):
            if grid[i][j] == 0: return (i, j)
    return None

# ── Backtracking với callback từng bước ──────────────────────────────────────
def run_backtracking_steps(grid, N, horiz, vert, step_cb=None, stop_flag=None):
    stats = [0]
    steps = []

    def solve(g):
        if stop_flag and stop_flag[0]: return False
        stats[0] += 1
        pos = find_empty(g, N)
        if not pos:
            return True
        r, c = pos
        for num in range(1, N+1):
            if is_safe(g, r, c, num, N, horiz, vert):
                g[r][c] = num
                steps.append(("place", r, c, num, stats[0]))
                if step_cb: step_cb("place", r, c, num, stats[0], [row[:] for row in g])
                if solve(g): return True
                g[r][c] = 0
                steps.append(("backtrack", r, c, 0, stats[0]))
                if step_cb: step_cb("backtrack", r, c, 0, stats[0], [row[:] for row in g])
        return False

    res = solve(grid)
    return res, stats[0], steps

# ── Forward Chaining / DPLL ──────────────────────────────────────────────────
def get_var_id(i, j, v, N):
    return (i-1)*N**2 + (j-1)*N + v

def build_full_kb(N, grid, horiz, vert):
    KB = []
    for i in range(1,N+1):
        for j in range(1,N+1):
            KB.append([get_var_id(i,j,v,N) for v in range(1,N+1)])
    for i in range(1,N+1):
        for j in range(1,N+1):
            for v1 in range(1,N+1):
                for v2 in range(v1+1,N+1):
                    KB.append([-get_var_id(i,j,v1,N), -get_var_id(i,j,v2,N)])
    for i in range(1,N+1):
        for j in range(1,N+1):
            if grid[i-1][j-1] != 0:
                KB.append([get_var_id(i,j,grid[i-1][j-1],N)])
    for i in range(1,N+1):
        for v in range(1,N+1):
            for j1 in range(1,N+1):
                for j2 in range(j1+1,N+1):
                    KB.append([-get_var_id(i,j1,v,N), -get_var_id(i,j2,v,N)])
    for j in range(1,N+1):
        for v in range(1,N+1):
            for i1 in range(1,N+1):
                for i2 in range(i1+1,N+1):
                    KB.append([-get_var_id(i1,j,v,N), -get_var_id(i2,j,v,N)])
    for r in range(N):
        for c in range(N-1):
            if horiz[r][c] == 1:
                for v1 in range(1,N+1):
                    for v2 in range(1,v1+1):
                        KB.append([-get_var_id(r+1,c+1,v1,N), -get_var_id(r+1,c+2,v2,N)])
            if horiz[r][c] == -1:
                for v1 in range(1,N+1):
                    for v2 in range(v1,N+1):
                        KB.append([-get_var_id(r+1,c+1,v1,N), -get_var_id(r+1,c+2,v2,N)])
    for r in range(N-1):
        for c in range(N):
            if vert[r][c] == 1:
                for v1 in range(1,N+1):
                    for v2 in range(1,v1+1):
                        KB.append([-get_var_id(r+1,c+1,v1,N), -get_var_id(r+2,c+1,v2,N)])
            if vert[r][c] == -1:
                for v1 in range(1,N+1):
                    for v2 in range(v1,N+1):
                        KB.append([-get_var_id(r+1,c+1,v1,N), -get_var_id(r+2,c+1,v2,N)])
    return KB

def unit_propagate(clauses, assignment):
    clauses_copy = [c[:] for c in clauses]
    asn = assignment.copy()
    while True:
        unit = next((c[0] for c in clauses_copy if len(c)==1), None)
        if unit is None: break
        var = abs(unit); val = unit > 0
        if var in asn and asn[var] != val: return False, [], {}
        asn[var] = val
        new_cls = []
        for c in clauses_copy:
            if unit in c: continue
            elif -unit in c:
                nc = [l for l in c if l != -unit]
                if not nc: return False, [], {}
                new_cls.append(nc)
            else: new_cls.append(c)
        clauses_copy = new_cls
    return True, clauses_copy, asn

def run_dpll(clauses):
    stats = [0]
    def dpll(cls, asn):
        stats[0] += 1
        ok, simp, new_asn = unit_propagate(cls, asn)
        if not ok: return False, {}
        if not simp: return True, new_asn
        chosen = abs(min(simp, key=len)[0])
        r1, a1 = dpll(simp + [[chosen]], new_asn)
        if r1: return True, a1
        return dpll(simp + [[-chosen]], new_asn)
    res, asn = dpll(clauses, {})
    return res, asn, stats[0]

def reconstruct_grid_from_dpll(asn, N):
    grid = [[0]*N for _ in range(N)]
    for i in range(1,N+1):
        for j in range(1,N+1):
            for v in range(1,N+1):
                var = get_var_id(i,j,v,N)
                if asn.get(var, False):
                    grid[i-1][j-1] = v
    return grid

# ── Backward Chaining ────────────────────────────────────────────────────────
def run_backward_chaining(grid, N, horiz, vert, query_i, query_j, query_v):
    stats = [0] 

    def ask(goal):
        stats[0] += 1
        pred = goal[0]
        args = goal[1:]

        if pred == "Val":
            r, c, v = args
            if ask(("Given", r, c, v)):
                return True
            if ask(("Empty", r, c)):
                if ask(("CheckRow", r, c, v)) and ask(("CheckCol", r, c, v)) and ask(("CheckRel", r, c, v)):
                    return True
            return False

        elif pred == "Given":
            r, c, v = args
            return grid[r][c] == v

        elif pred == "Empty":
            r, c = args
            return grid[r][c] == 0

        elif pred == "CheckRow":
            r, c, v = args
            for j in range(N):
                if j != c and grid[r][j] == v:
                    return False
            return True

        elif pred == "CheckCol":
            r, c, v = args
            for i in range(N):
                if i != r and grid[i][c] == v:
                    return False
            return True

        elif pred == "CheckRel":
            r, c, v = args
            if c > 0 and grid[r][c-1] != 0:
                if horiz[r][c-1] == 1 and not (grid[r][c-1] < v): return False
                if horiz[r][c-1] == -1 and not (grid[r][c-1] > v): return False
            if c < N-1 and grid[r][c+1] != 0:
                if horiz[r][c] == 1 and not (v < grid[r][c+1]): return False
                if horiz[r][c] == -1 and not (v > grid[r][c+1]): return False
            if r > 0 and grid[r-1][c] != 0:
                if vert[r-1][c] == 1 and not (grid[r-1][c] < v): return False
                if vert[r-1][c] == -1 and not (grid[r-1][c] > v): return False
            if r < N-1 and grid[r+1][c] != 0:
                if vert[r][c] == 1 and not (v < grid[r+1][c]): return False
                if vert[r][c] == -1 and not (v > grid[r+1][c]): return False
            return True

        return False

    res = ask(("Val", query_i, query_j, query_v))
    return res, stats[0]

# ── A* Search (NÂNG CẤP) ─────────────────────────────────────────────────────
def get_advanced_heuristic_mrv(grid, N, horiz, vert):
    domains = {}
    empty_count = 0

    # BƯỚC 1: Khởi tạo miền giá trị (Domain) bằng Forward Checking
    for r in range(N):
        for c in range(N):
            if grid[r][c] == 0:
                empty_count += 1
                valid_vals = []
                for v in range(1, N + 1):
                    if is_safe(grid, r, c, v, N, horiz, vert):
                        valid_vals.append(v)
                
                if not valid_vals:
                    return float('inf'), None  # Vô nghiệm sớm
                domains[(r, c)] = valid_vals

    # BƯỚC 2: Rút gọn miền giá trị (Naked Singles)
    changed = True
    while changed:
        changed = False
        for (r, c), valid_vals in list(domains.items()):
            if len(valid_vals) == 1:
                fixed_val = valid_vals[0]
                for (r2, c2) in domains:
                    if (r2, c2) != (r, c) and (r2 == r or c2 == c):
                        if fixed_val in domains[(r2, c2)]:
                            domains[(r2, c2)].remove(fixed_val)
                            changed = True
                            if not domains[(r2, c2)]:
                                return float('inf'), None

    # BƯỚC 3: CẢI TIẾN TIE-BREAKER CHO FUTOSHIKI (Inequality Degree)
    min_options = float('inf')
    best_pos = None
    max_ineq_degree = -1

    for pos, valid_vals in domains.items():
        options = len(valid_vals)
        r, c = pos
        
        # Đếm số lượng ràng buộc DẤU (<, >) chạm vào ô này
        ineq_count = 0
        if c > 0 and horiz[r][c-1] != 0: ineq_count += 1
        if c < N-1 and horiz[r][c] != 0: ineq_count += 1
        if r > 0 and vert[r-1][c] != 0: ineq_count += 1
        if r < N-1 and vert[r][c] != 0: ineq_count += 1

        if options < min_options:
            min_options = options
            best_pos = pos
            max_ineq_degree = ineq_count
        elif options == min_options:
            # Khi MRV hòa, BẮT BUỘC ưu tiên ô bị kẹp bởi nhiều dấu <, > hơn
            if ineq_count > max_ineq_degree:
                best_pos = pos
                max_ineq_degree = ineq_count

    return empty_count, best_pos

def run_astar_steps(initial_grid, N, horiz, vert, step_cb=None, stop_flag=None):
    g0 = sum(1 for r in range(N) for c in range(N) if initial_grid[r][c] != 0)
    h0, mrv0 = get_advanced_heuristic_mrv(initial_grid, N, horiz, vert)
    if h0 == float('inf'): return False, None, 0
    pq = []
    tb = itertools.count()
    
    # Thêm một tuple rỗng () ở cuối để lưu "hành động cuối cùng (last_move)"
    heapq.heappush(pq, (g0+h0, -g0, next(tb), initial_grid, mrv0, ()))
    nodes = 0
    
    while pq:
        if stop_flag and stop_flag[0]: return False, None, nodes
        
        # Bổ sung last_move khi lấy ra khỏi Queue
        f, neg_g, _, cur_grid, pos, last_move = heapq.heappop(pq)
        g = -neg_g; nodes += 1
        
        # UPDATE UI TẠI ĐÂY (Khi node thực sự được duyệt)
        if step_cb and last_move:
            step_cb("place", last_move[0], last_move[1], last_move[2], nodes, cur_grid)
            
        if not pos:
            if step_cb: step_cb("done", -1, -1, -1, nodes, cur_grid)
            return True, cur_grid, nodes
            
        r, c = pos
        for num in range(1, N+1):
            if is_safe(cur_grid, r, c, num, N, horiz, vert):
                child = [row[:] for row in cur_grid]
                child[r][c] = num
                ch, cmrv = get_advanced_heuristic_mrv(child, N, horiz, vert)
                if ch != float('inf'):
                    # Lưu kèm hành động (r, c, num) vừa thực hiện để truyền xuống node con
                    heapq.heappush(pq, (g+1+ch, -(g+1), next(tb), child, cmrv, (r, c, num)))
                    
    return False, None, nodes

# ── Benchmark wrapper ─────────────────────────────────────────────────────────
def benchmark(func, *args):
    tracemalloc.start()
    t0 = time.perf_counter()
    result = func(*args)
    t1 = time.perf_counter()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, t1-t0, peak/(1024*1024)

# ═══════════════════════════════════════════════════════════════════════════════
# WIDGET: BẢNG FUTOSHIKI
# ═══════════════════════════════════════════════════════════════════════════════

class FutoshikiBoard(tk.Canvas):
    CELL = 54
    PAD  = 28

    def __init__(self, parent, N=4, **kw):
        self.N = N
        size = N * self.CELL + (N-1)*4 + self.PAD*2
        super().__init__(parent, width=size, height=size,
                         bg=THEME["surface"], highlightthickness=0, **kw)
        self.grid_data  = [[0]*N for _ in range(N)]
        self.horiz      = [[0]*(N-1) for _ in range(N)]
        self.vert       = [[0]*N for _ in range(N-1)]
        self.given_cells = set()
        self.highlight   = None   # (r,c) ô đang được đặt
        self.hl_type     = None   # "place" | "backtrack"
        self.cell_ids    = {}
        self.draw_board()

    def setup(self, N, grid, horiz, vert):
        self.N = N
        self.grid_data = [row[:] for row in grid]
        self.horiz = horiz
        self.vert  = vert
        self.given_cells = {(r,c) for r in range(N) for c in range(N) if grid[r][c] != 0}
        self.highlight = None
        size = N * self.CELL + (N-1)*4 + self.PAD*2
        self.config(width=size, height=size)
        self.draw_board()

    def _cell_xy(self, r, c):
        x = self.PAD + c*(self.CELL+4) + self.CELL//2
        y = self.PAD + r*(self.CELL+4) + self.CELL//2
        return x, y

    def draw_board(self):
        self.delete("all")
        N = self.N
        C = self.CELL

        for r in range(N):
            for c in range(N):
                x, y = self._cell_xy(r, c)
                x0, y0 = x - C//2, y - C//2
                x1, y1 = x + C//2, y + C//2

                # Màu ô
                if self.highlight == (r, c):
                    fill = THEME["accent"] if self.hl_type == "place" else THEME["red"]
                    fill_dark = fill
                elif (r, c) in self.given_cells:
                    fill = THEME["surface3"]
                    fill_dark = THEME["surface3"]
                else:
                    fill = THEME["surface2"]
                    fill_dark = THEME["surface2"]

                # Bo góc
                self.create_rectangle(x0+4, y0, x1-4, y1, fill=fill, outline="", width=0)
                self.create_rectangle(x0, y0+4, x1, y1-4, fill=fill, outline="", width=0)
                self.create_oval(x0, y0, x0+8, y0+8, fill=fill, outline="")
                self.create_oval(x1-8, y0, x1, y0+8, fill=fill, outline="")
                self.create_oval(x0, y1-8, x0+8, y1, fill=fill, outline="")
                self.create_oval(x1-8, y1-8, x1, y1, fill=fill, outline="")

                # Số
                val = self.grid_data[r][c]
                if val != 0:
                    if (r, c) in self.given_cells:
                        color = THEME["text"]
                        font = ("Consolas", 18, "bold")
                    elif self.highlight == (r, c) and self.hl_type == "backtrack":
                        color = THEME["red"]
                        font = ("Consolas", 18, "bold")
                    else:
                        color = THEME["accent"]
                        font = ("Consolas", 18, "bold")
                    self.create_text(x, y, text=str(val), fill=color, font=font)

        # Vẽ ràng buộc ngang
        for r in range(N):
            for c in range(N-1):
                con = self.horiz[r][c]
                if con == 0: continue
                x1, y1 = self._cell_xy(r, c)
                x2, y2 = self._cell_xy(r, c+1)
                mx = (x1 + x2) // 2
                sym = "<" if con == 1 else ">"
                self.create_text(mx, y1, text=sym, fill=THEME["yellow"],
                                 font=("Consolas", 13, "bold"))

        # Vẽ ràng buộc dọc
        for r in range(N-1):
            for c in range(N):
                con = self.vert[r][c]
                if con == 0: continue
                x1, y1 = self._cell_xy(r, c)
                x2, y2 = self._cell_xy(r+1, c)
                my = (y1 + y2) // 2
                sym = "∧" if con == 1 else "∨"
                self.create_text(x1, my, text=sym, fill=THEME["yellow"],
                                 font=("Consolas", 13, "bold"))

    def update_cell(self, r, c, val, hl_type=None):
        self.grid_data[r][c] = val
        self.highlight = (r, c) if val != 0 or hl_type == "backtrack" else None
        self.hl_type = hl_type
        self.draw_board()

    def show_final(self, grid):
        self.grid_data = [row[:] for row in grid]
        self.highlight = None
        self.draw_board()

    def reset_to(self, grid):
        self.grid_data = [row[:] for row in grid]
        self.highlight = None
        self.draw_board()


# ═══════════════════════════════════════════════════════════════════════════════
# PANEL: LOG BƯỚC GIẢI
# ═══════════════════════════════════════════════════════════════════════════════

class StepLog(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=THEME["surface"], **kw)
        tk.Label(self, text="STEP LOG", font=FONT_SMALL, bg=THEME["surface"],
                 fg=THEME["text_dim"]).pack(anchor="w", padx=10, pady=(10,4))
        self.text = tk.Text(self, bg=THEME["surface2"], fg=THEME["text_muted"],
                            font=("Courier New", 9), relief="flat", bd=0,
                            state="disabled", wrap="word")
        sb = tk.Scrollbar(self, command=self.text.yview, bg=THEME["surface"])
        self.text.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True, padx=(10,0), pady=(0,10))
        self.text.tag_config("place",     foreground=THEME["accent"])
        self.text.tag_config("backtrack", foreground=THEME["red"])
        self.text.tag_config("info",      foreground=THEME["green"])
        self.text.tag_config("done",      foreground=THEME["yellow"])
        self.count = 0

    def clear(self):
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.config(state="disabled")
        self.count = 0

    def log(self, msg, tag="info"):
        self.count += 1
        self.text.config(state="normal")
        self.text.insert("end", f"[{self.count:>5}] {msg}\n", tag)
        self.text.see("end")
        self.text.config(state="disabled")


# ═══════════════════════════════════════════════════════════════════════════════
# PANEL: STATS CARD
# ═══════════════════════════════════════════════════════════════════════════════

class StatsPanel(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=THEME["bg"], **kw)
        self.cards = {}
        metrics = [
            ("time",  "Runtime",   "–– s",   THEME["accent"]),
            ("nodes", "Nodes",     "––",     THEME["green"]),
            ("ram",   "Peak RAM",  "–– MB",  THEME["yellow"]),
            ("status","Status",    "Ready",  THEME["text_muted"]),
        ]
        for i, (key, label, default, color) in enumerate(metrics):
            f = tk.Frame(self, bg=THEME["surface"], padx=14, pady=12)
            f.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            self.columnconfigure(i, weight=1)
            tk.Label(f, text=label.upper(), font=FONT_SMALL, bg=THEME["surface"],
                     fg=THEME["text_dim"]).pack(anchor="w")
            lbl = tk.Label(f, text=default, font=("Consolas", 17, "bold"),
                           bg=THEME["surface"], fg=color)
            lbl.pack(anchor="w", pady=(4,0))
            self.cards[key] = lbl

    def update(self, time_s=None, nodes=None, ram=None, status=None, status_color=None):
        if time_s is not None:
            self.cards["time"].config(text=f"{time_s:.4f} s")
        if nodes is not None:
            self.cards["nodes"].config(text=f"{nodes:,}")
        if ram is not None:
            self.cards["ram"].config(text=f"{ram:.3f} MB")
        if status is not None:
            self.cards["status"].config(
                text=status,
                fg=status_color or THEME["text_muted"]
            )

    def reset(self):
        self.cards["time"].config(text="–– s")
        self.cards["nodes"].config(text="––")
        self.cards["ram"].config(text="–– MB")
        self.cards["status"].config(text="Ready", fg=THEME["text_muted"])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: SOLVER (trực quan từng bước)
# ═══════════════════════════════════════════════════════════════════════════════

class SolverTab(tk.Frame):
    MAX_VISUAL_STEPS = 800

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=THEME["bg"], **kw)
        self.N = 4
        self.grid_orig = [[0]*4 for _ in range(4)]
        self.horiz = [[0]*3 for _ in range(4)]
        self.vert  = [[0]*4 for _ in range(3)]
        self.current_file = None
        self.file_list    = []          # danh sách tất cả files tìm được
        self.running      = False
        self.solve_all_mode = False
        self.stop_flag    = [False]
        self.speed        = 30
        self._file_row_widgets = {}     # path -> frame widget trong list
        self._build_ui()
        self._auto_discover_files()

    # ── AUTO-DISCOVER ───────────────────────────────────────────────────────
    def _auto_discover_files(self):
        """Tìm tất cả input-*.txt trong cùng thư mục script và thư mục Inputs/"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        patterns = [
            os.path.join(script_dir, "input-*.txt"),
            os.path.join(script_dir, "Inputs", "input-*.txt"),
            os.path.join(script_dir, "inputs", "input-*.txt"),
        ]
        found = []
        for pat in patterns:
            found.extend(sorted(glob.glob(pat)))
            
        seen = set()
        unique = []
        for f in found:
            norm_path = os.path.normcase(os.path.abspath(f))
            if norm_path not in seen:
                seen.add(norm_path)
                unique.append(f)
                
        if unique:
            self._populate_file_list(unique)
            self._select_file(unique[0])
        else:
            self.log.log("Không tìm thấy input-*.txt trong thư mục hiện tại.", "backtrack")
            self.log.log("Dùng 📂 Open Folder để chọn thư mục chứa file.", "info")

    # ── BUILD UI ────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ──
        hdr = tk.Frame(self, bg=THEME["bg"])
        hdr.pack(fill="x", padx=16, pady=(14,6))
        tk.Label(hdr, text="FUTOSHIKI", font=("Consolas", 22, "bold"),
                 bg=THEME["bg"], fg=THEME["accent"]).pack(side="left")
        tk.Label(hdr, text=" SOLVER", font=("Consolas", 22, "bold"),
                 bg=THEME["bg"], fg=THEME["text"]).pack(side="left")
        self._btn(hdr, "📂 Open Folder", self._open_folder, THEME["surface2"]).pack(side="right", padx=3)

        # ── Controls row ──
        ctrl_wrap = tk.Frame(self, bg=THEME["bg"])
        ctrl_wrap.pack(fill="x", padx=16, pady=(0,6))

        # Algo buttons
        tk.Label(ctrl_wrap, text="Algorithm:", font=FONT_BODY,
                 bg=THEME["bg"], fg=THEME["text_muted"]).pack(side="left", padx=(0,6))
        self.algo_var = tk.StringVar(value="A*")
        for algo in ["BT", "FC", "BC", "A*"]:
            color = ALGO_COLORS[algo]
            tk.Radiobutton(ctrl_wrap, text=algo, variable=self.algo_var, value=algo,
                           font=("Consolas", 11, "bold"),
                           bg=THEME["bg"], fg=color, selectcolor=THEME["surface"],
                           activebackground=THEME["bg"], activeforeground=color,
                           indicatoron=0, relief="flat", padx=10, pady=4,
                           bd=1, cursor="hand2",
                           command=self._algo_changed).pack(side="left", padx=2)

        # Speed
        tk.Label(ctrl_wrap, text="  Speed:", font=FONT_BODY,
                 bg=THEME["bg"], fg=THEME["text_muted"]).pack(side="left", padx=(10,4))
        self.speed_var = tk.IntVar(value=30)
        tk.Scale(ctrl_wrap, from_=1, to=200, orient="horizontal",
                 variable=self.speed_var, bg=THEME["bg"], fg=THEME["text_muted"],
                 troughcolor=THEME["surface2"], activebackground=THEME["accent"],
                 highlightthickness=0, relief="flat", length=140, showvalue=False,
                 command=lambda v: setattr(self, 'speed', int(v))).pack(side="left")
        tk.Label(ctrl_wrap, text="S←→F", font=FONT_SMALL,
                 bg=THEME["bg"], fg=THEME["text_dim"]).pack(side="left", padx=4)

        # Action buttons
        self.btn_solve     = self._btn(ctrl_wrap, "▶ Solve",     self._start_solve,    THEME["accent"], fg="#000")
        self.btn_solve_all = self._btn(ctrl_wrap, "⏭ Solve All", self._start_solve_all, "#1D4ED8")
        self.btn_stop      = self._btn(ctrl_wrap, "■ Stop",      self._stop,            THEME["red"])
        self.btn_reset     = self._btn(ctrl_wrap, "↺ Reset",     self._reset,           THEME["surface2"])
        for b in [self.btn_solve, self.btn_solve_all, self.btn_stop, self.btn_reset]:
            b.pack(side="left", padx=3)

        # BC note
        self.bc_note = tk.Label(self, text="", font=FONT_SMALL,
                                bg=THEME["bg"], fg=THEME["text_muted"],
                                wraplength=900, justify="left")
        self.bc_note.pack(fill="x", padx=16, pady=(0,4))

        # ── Body: file list | board | log ──
        body = tk.Frame(self, bg=THEME["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=(0,14))
        body.columnconfigure(0, weight=0)   # file list
        body.columnconfigure(1, weight=0)   # board
        body.columnconfigure(2, weight=1)   # right panel
        body.rowconfigure(0, weight=1)

        # ── File list panel ──
        fl_wrap = tk.Frame(body, bg=THEME["surface"], width=170)
        fl_wrap.grid(row=0, column=0, sticky="nsew", padx=(0,10))
        fl_wrap.pack_propagate(False)

        fl_hdr = tk.Frame(fl_wrap, bg=THEME["surface2"])
        fl_hdr.pack(fill="x")
        tk.Label(fl_hdr, text="INPUT FILES", font=FONT_SMALL,
                 bg=THEME["surface2"], fg=THEME["text_dim"],
                 pady=6, padx=8).pack(side="left")
        self.file_count_lbl = tk.Label(fl_hdr, text="0 files",
                                       font=FONT_SMALL, bg=THEME["surface2"],
                                       fg=THEME["text_dim"])
        self.file_count_lbl.pack(side="right", padx=6)

        fl_canvas = tk.Canvas(fl_wrap, bg=THEME["surface"], highlightthickness=0)
        fl_sb = tk.Scrollbar(fl_wrap, orient="vertical", command=fl_canvas.yview,
                             bg=THEME["surface"])
        fl_canvas.configure(yscrollcommand=fl_sb.set)
        fl_sb.pack(side="right", fill="y")
        fl_canvas.pack(side="left", fill="both", expand=True)
        self.fl_inner = tk.Frame(fl_canvas, bg=THEME["surface"])
        self.fl_canvas_win = fl_canvas.create_window((0,0), window=self.fl_inner, anchor="nw")
        self.fl_inner.bind("<Configure>",
            lambda e: fl_canvas.configure(scrollregion=fl_canvas.bbox("all")))
        fl_canvas.bind("<Configure>",
            lambda e: fl_canvas.itemconfig(self.fl_canvas_win, width=e.width))

        # ── Board ──
        board_wrap = tk.Frame(body, bg=THEME["surface"])
        board_wrap.grid(row=0, column=1, sticky="n", padx=(0,10))
        self.board = FutoshikiBoard(board_wrap, N=self.N)
        self.board.pack(padx=10, pady=10)

        # ── Right: stats + log ──
        right = tk.Frame(body, bg=THEME["bg"])
        right.grid(row=0, column=2, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        self.stats = StatsPanel(right)
        self.stats.grid(row=0, column=0, sticky="ew", pady=(0,10))

        self.log = StepLog(right)
        self.log.grid(row=1, column=0, sticky="nsew")

    # ── HELPERS ─────────────────────────────────────────────────────────────
    def _btn(self, parent, text, cmd, bg, fg=None):
        return tk.Button(parent, text=text, command=cmd, font=FONT_BODY,
                         bg=bg, fg=fg or THEME["text"], relief="flat",
                         padx=12, pady=6, cursor="hand2",
                         activebackground=THEME["surface3"],
                         activeforeground=THEME["text"], bd=0)

    def _algo_changed(self):
        algo = self.algo_var.get()
        self.bc_note.config(
            text=("ℹ  BC chỉ kiểm tra 1 ô mồi từ Horn KB — bảng nghiệm hiển thị bằng A*."
                  if algo == "BC" else ""))

    def _open_folder(self):
        folder = filedialog.askdirectory(title="Chọn thư mục chứa input-*.txt")
        if not folder: return
        files = sorted(glob.glob(os.path.join(folder, "input-*.txt")))
        if not files:
            messagebox.showinfo("Không tìm thấy",
                                f"Không có file input-*.txt trong:\n{folder}")
            return
        self._populate_file_list(files)
        self._select_file(files[0])

    # ── FILE LIST ───────────────────────────────────────────────────────────
    def _populate_file_list(self, files):
        """Render lại danh sách file trong panel trái."""
        for w in self.fl_inner.winfo_children():
            w.destroy()
        self._file_row_widgets.clear()
        self.file_list = files
        self.file_count_lbl.config(text=f"{len(files)} files")

        for path in files:
            fname = os.path.basename(path)
            row = tk.Frame(self.fl_inner, bg=THEME["surface"], cursor="hand2")
            row.pack(fill="x", pady=1)

            # Status dot (●)
            dot = tk.Label(row, text="●", font=("Consolas", 8),
                           bg=THEME["surface"], fg=THEME["text_dim"], padx=4)
            dot.pack(side="left")

            lbl = tk.Label(row, text=fname, font=("Consolas", 10),
                           bg=THEME["surface"], fg=THEME["text_muted"],
                           anchor="w", padx=4, pady=5)
            lbl.pack(side="left", fill="x", expand=True)

            # Click → select
            for w in (row, dot, lbl):
                w.bind("<Button-1>", lambda e, p=path: self._select_file(p))
                w.bind("<Enter>",    lambda e, r=row: r.config(bg=THEME["surface2"]))
                w.bind("<Leave>",    lambda e, r=row, p=path: r.config(
                    bg=THEME["accent"] if self.current_file == p else THEME["surface"]))

            self._file_row_widgets[path] = {"row": row, "dot": dot, "lbl": lbl}

    def _select_file(self, path):
        """Load file và highlight row đang chọn."""
        if self.running: return
        # Reset style tất cả rows
        for p, w in self._file_row_widgets.items():
            is_sel = (p == path)
            w["row"].config(bg=THEME["accent"] if is_sel else THEME["surface"])
            w["lbl"].config(fg="#000" if is_sel else THEME["text_muted"],
                            font=("Consolas", 10, "bold") if is_sel else ("Consolas", 10))
            w["dot"].config(fg="#000" if is_sel else THEME["text_dim"],
                            bg=THEME["accent"] if is_sel else THEME["surface"])
        try:
            self.N, self.grid_orig, self.horiz, self.vert = read_futoshiki_input(path)
            self.current_file = path
            self.board.setup(self.N, self.grid_orig, self.horiz, self.vert)
            self.stats.reset()
            self.log.clear()
            self.log.log(f"Loaded: {os.path.basename(path)}  (N={self.N}×{self.N})", "info")
        except Exception as e:
            messagebox.showerror("Lỗi đọc file", str(e))

    def _set_file_status(self, path, status):
        """Cập nhật dot màu: 'pending'|'running'|'done'|'unsolvable'|'error'"""
        if path not in self._file_row_widgets: return
        colors = {
            "pending":    THEME["text_dim"],
            "running":    THEME["yellow"],
            "done":       THEME["green"],
            "unsolvable": THEME["red"],
            "error":      THEME["red"],
        }
        w = self._file_row_widgets[path]
        c = colors.get(status, THEME["text_dim"])
        w["dot"].config(fg=c)

    # ── SOLVE SINGLE ────────────────────────────────────────────────────────
    def _start_solve(self):
        if self.running: return
        if not self.current_file:
            messagebox.showinfo("Thông báo", "Chưa chọn file input!")
            return
        self.solve_all_mode = False
        self.stop_flag = [False]
        self.running   = True
        self.stats.reset()
        self.log.clear()
        self.board.reset_to(self.grid_orig)
        algo = self.algo_var.get()
        self.log.log(f"▶ [{algo}]  {os.path.basename(self.current_file)}  N={self.N}", "info")
        self._set_file_status(self.current_file, "running")
        threading.Thread(
            target=self._solve_one,
            args=(self.current_file, self.N, self.grid_orig, self.horiz, self.vert,
                  algo, True),
            daemon=True).start()

    # ── SOLVE ALL ───────────────────────────────────────────────────────────
    def _start_solve_all(self):
        if self.running: return
        if not self.file_list:
            messagebox.showinfo("Thông báo", "Chưa có file nào trong danh sách!")
            return
        self.solve_all_mode = True
        self.stop_flag = [False]
        self.running   = True
        # Reset tất cả dot về pending
        for p in self._file_row_widgets:
            self._set_file_status(p, "pending")
        algo = self.algo_var.get()
        self.log.clear()
        self.log.log(f"⏭ Solve All ({len(self.file_list)} files)  [{algo}]", "info")
        threading.Thread(target=self._solve_all_thread, args=(algo,), daemon=True).start()

    def _solve_all_thread(self, algo):
        for path in self.file_list:
            if self.stop_flag[0]: break
            try:
                N, grid_o, horiz, vert = read_futoshiki_input(path)
            except Exception as e:
                self.after(0, lambda p=path: self._set_file_status(p, "error"))
                self.after(0, lambda p=path, e=e:
                           self.log.log(f"✗ {os.path.basename(p)}: {e}", "backtrack"))
                continue
            # Select + highlight file đang chạy
            self.after(0, lambda p=path, n=N, g=grid_o, h=horiz, v=vert:
                       self._switch_to_file(p, n, g, h, v))
            # Đợi UI cập nhật
            time.sleep(0.05)
            self.after(0, lambda p=path: self._set_file_status(p, "running"))
            # Chạy thuật toán (sync, trong thread này)
            self._solve_one(path, N, grid_o, horiz, vert, algo, visual=True)
            # Chờ animation xong trước khi qua file tiếp
            while self.running and not self.stop_flag[0]:
                time.sleep(0.05)
                # running sẽ được set False bởi _finish_one() khi xong
                break

        self.after(0, lambda: setattr(self, 'running', False))
        if not self.stop_flag[0]:
            self.after(0, lambda: self.log.log("✓ Đã giải xong tất cả files.", "done"))

    def _switch_to_file(self, path, N, grid_o, horiz, vert):
        """Gọi từ after() — cập nhật UI sang file mới."""
        for p, w in self._file_row_widgets.items():
            is_sel = (p == path)
            w["row"].config(bg=THEME["accent"] if is_sel else THEME["surface"])
            w["lbl"].config(fg="#000" if is_sel else THEME["text_muted"],
                            font=("Consolas", 10, "bold") if is_sel else ("Consolas", 10))
            w["dot"].config(bg=THEME["accent"] if is_sel else THEME["surface"])
        self.N, self.grid_orig, self.horiz, self.vert = N, grid_o, horiz, vert
        self.current_file = path
        self.board.setup(N, grid_o, horiz, vert)
        self.stats.reset()
        self.log.log(f"\n── {os.path.basename(path)}  (N={N}×{N}) ──", "info")

    # ── CORE SOLVE ──────────────────────────────────────────────────────────
    def _solve_one(self, path, N, grid_o, horiz, vert, algo, visual=True):
        """Chạy một thuật toán trên một file. Luôn chạy trong thread."""
        grid = copy.deepcopy(grid_o)
        step_count = [0]

        def step_cb(action, r, c, val, nodes, grid_snap):
            if self.stop_flag[0]: return
            step_count[0] += 1
            if step_count[0] > self.MAX_VISUAL_STEPS: return

            def ui():
                if self.stop_flag[0]: return
                if action == "place":
                    self.board.update_cell(r, c, val, "place")
                    self.log.log(f"  Đặt [{r+1},{c+1}]={val}  node#{nodes}", "place")
                elif action == "backtrack":
                    self.board.update_cell(r, c, 0, "backtrack")
                    self.log.log(f"  Quay lui [{r+1},{c+1}]  node#{nodes}", "backtrack")
                self.stats.update(nodes=nodes, status="Đang giải…",
                                  status_color=THEME["yellow"])
            self.after(0, ui)
            time.sleep(max(1, self.speed) / 1000.0)

        cb = step_cb if visual else None

        tracemalloc.start()
        t0 = time.perf_counter()
        final_grid = None

        try:
            if algo == "BT":
                res, nodes, _ = run_backtracking_steps(grid, N, horiz, vert, cb, self.stop_flag)
                final_grid = grid if res else None

            elif algo == "FC":
                KB = build_full_kb(N, grid_o, horiz, vert)
                self.after(0, lambda: self.log.log(
                    f"  CNF KB: {len(KB):,} clauses", "info"))
                res, asn, nodes = run_dpll(KB)
                final_grid = reconstruct_grid_from_dpll(asn, N) if res else None
                if final_grid:
                    self.after(0, lambda g=final_grid: self.board.show_final(g))

            elif algo == "BC":
                # Tìm 1 ô trống đầu tiên để Query
                ti, tj = -1, -1
                for row in range(N):
                    for col in range(N):
                        if grid_o[row][col] == 0:
                            ti, tj = row, col; break
                    if ti != -1: break
                
                self.after(0, lambda: self.log.log(f"  Prolog Query: ?- Val({ti+1},{tj+1}, V)", "info"))
                
                total_nodes = 0
                valid_vals = []
                for v in range(1, N + 1):
                    res, nds = run_backward_chaining(grid_o, N, horiz, vert, ti, tj, v)
                    total_nodes += nds
                    if res: valid_vals.append(v)
                
                msg = f"  ✓ SLD Resolution tìm được miền giá trị hợp lệ: {valid_vals}" if valid_vals else "  ✗ Không có giá trị hợp lệ nào"
                tag = "done" if valid_vals else "backtrack"
                self.after(0, lambda m=msg, t=tag: self.log.log(m, t))
                
                # Để hiển thị nghiệm cuối cùng lên UI, ta mượn A* giải nhanh phần còn lại
                g2 = copy.deepcopy(grid_o)
                _, final_grid, _ = run_astar_steps(g2, N, horiz, vert)
                nodes = total_nodes # Trả về số node suy diễn của BC để hiển thị Stats

            elif algo == "A*":
                res, final_grid, nodes = run_astar_steps(
                    grid, N, horiz, vert, cb, self.stop_flag)

        except Exception as ex:
            self.after(0, lambda e=ex: self.log.log(f"  ✗ Lỗi: {e}", "backtrack"))
            nodes = 0
            res = False

        t1 = time.perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        elapsed = t1 - t0
        ram = peak / (1024*1024)

        if self.stop_flag[0]: return

        def finish(p=path, fg=final_grid, e=elapsed, n=nodes, rm=ram, r=res):
            self.running = False
            if fg:
                self.board.show_final(fg)
                self.stats.update(time_s=e, nodes=n, ram=rm,
                                  status="✓ Solved!", status_color=THEME["green"])
                self.log.log(
                    f"  ✓ {os.path.basename(p)}  {e:.4f}s  {n:,} nodes  {rm:.3f}MB", "done")
                self._set_file_status(p, "done")
            else:
                self.stats.update(time_s=e, nodes=n, ram=rm,
                                  status="✗ Vô nghiệm", status_color=THEME["red"])
                self.log.log(f"  ✗ {os.path.basename(p)} — Vô nghiệm", "backtrack")
                self._set_file_status(p, "unsolvable")

        self.after(0, finish)

    def _stop(self):
        self.stop_flag[0] = True
        self.running = False
        self.log.log("⏹ Dừng bởi người dùng.", "info")

    def _reset(self):
        self.stop_flag[0] = True
        self.running = False
        if self.current_file:
            self.board.reset_to(self.grid_orig)
        self.stats.reset()
        self.log.clear()
        for p in self._file_row_widgets:
            self._set_file_status(p, "pending")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: BENCHMARK & BIỂU ĐỒ SO SÁNH
# ═══════════════════════════════════════════════════════════════════════════════

# Số liệu đã được cập nhật từ kết quả Benchmark với A* tối ưu mới nhất!
# Cập nhật vào futoshiki_ui.py (Phần Tab 2)
BENCHMARK_DATA = [
    {"file":"input-01","N":4,"sol":True,
     "BT":(0.0019,17,0.001),"FC":(0.0035,1,0.035),"BC":(0.0001,21,0.002),"A*":(0.0016,13,0.001)},
    {"file":"input-02","N":4,"sol":True,
     "BT":(0.0011,59,0.001),"FC":(0.0176,24,0.144),"BC":(0.0001,24,0.002),"A*":(0.0037,17,0.003)},
    {"file":"input-03","N":5,"sol":True,
     "BT":(0.0009,76,0.001),"FC":(0.0169,1,0.111),"BC":(0.0001,27,0.002),"A*":(0.0034,18,0.002)},
    {"file":"input-04","N":5,"sol":True,
     "BT":(0.0025,152,0.002),"FC":(0.0365,24,0.446),"BC":(0.0001,30,0.002),"A*":(0.0885,411,0.005)},
    {"file":"input-05","N":6,"sol":True,
     "BT":(0.6189,32842,0.002),"FC":(0.8645,449,1.084),"BC":(0.0001,33,0.002),"A*":(0.0463,102,0.005)},
    {"file":"input-06","N":6,"sol":False,
     "BT":(2.6390,154015,0.001),"FC":(0.0278,1,0.202),"BC":(0.0001,34,0.003),"A*":(0.0016,2,0.002)},
    {"file":"input-07","N":7,"sol":True,
     "BT":(0.0028,102,0.002),"FC":(0.4244,115,0.801),"BC":(0.0001,37,0.003),"A*":(0.0416,107,0.004)},
    {"file":"input-08","N":7,"sol":False,
     "BT":(0.0132,782,0.001),"FC":(0.1570,1,0.382),"BC":(0.0001,37,0.003),"A*":(0.0009,0,0.001)},
    {"file":"input-09","N":9,"sol":True,
     "BT":(6.8041,217488,0.004),"FC":(2.1809,94,2.659),"BC":(0.0002,49,0.004),"A*":(0.1969,216,0.030)},
    {"file":"input-10","N":9,"sol":True,
     "BT":(11.2362,383211,0.002),"FC":(2.1293,20,1.112),"BC":(0.0002,48,0.004),"A*":(0.0661,95,0.005)},
]

class BenchmarkTab(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=THEME["bg"], **kw)
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=THEME["bg"])
        hdr.pack(fill="x", padx=20, pady=(16,4))
        tk.Label(hdr, text="ALGORITHM", font=("Consolas", 24, "bold"),
                 bg=THEME["bg"], fg=THEME["accent"]).pack(side="left")
        tk.Label(hdr, text=" BENCHMARK", font=("Consolas", 24, "bold"),
                 bg=THEME["bg"], fg=THEME["text"]).pack(side="left")
        tk.Label(hdr, text="  Dữ liệu thực — 10 test cases, N ∈ {4,5,6,7,9}",
                 font=FONT_SMALL, bg=THEME["bg"], fg=THEME["text_dim"]).pack(side="left", padx=10)

        # Re-run button
        tk.Button(hdr, text="⟳  Re-run Benchmark", command=self._rerun,
                  font=FONT_BODY, bg=THEME["surface2"], fg=THEME["text"],
                  relief="flat", padx=12, pady=6, cursor="hand2").pack(side="right")

        # Notebook: Charts / Table
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=20, pady=(8,16))

        self.chart_frame = tk.Frame(nb, bg=THEME["bg"])
        self.table_frame = tk.Frame(nb, bg=THEME["bg"])
        nb.add(self.chart_frame, text="  📈 Charts  ")
        nb.add(self.table_frame, text="  📋 Table  ")

        self._build_charts()
        self._build_table()

    def _build_charts(self):
        plt.style.use("dark_background")
        fig = plt.figure(figsize=(13, 8), facecolor=THEME["bg"])
        gs  = gridspec.GridSpec(2, 2, figure=fig,
                                hspace=0.45, wspace=0.32,
                                left=0.07, right=0.97,
                                top=0.92, bottom=0.10)

        data = BENCHMARK_DATA
        labels = [f"#{d['file'].replace('input-','')}" for d in data]
        algos  = ["BT","FC","BC","A*"]
        colors = [THEME["bt_color"], THEME["fc_color"], THEME["bc_color"], THEME["as_color"]]
        dashes = [None, (6,3), (3,3), (8,3,2,3)]
        markers = ["o","s","^","D"]

        idx = list(range(len(data)))

        # ── Chart 1: Runtime ──
        ax1 = fig.add_subplot(gs[0, 0])
        for i, algo in enumerate(algos):
            vals = [max(d[algo][0], 1e-5) for d in data]
            ls = "--" if dashes[i] else "-"
            ax1.semilogy(idx, vals, color=colors[i], marker=markers[i],
                         markersize=5, linewidth=1.8, linestyle=ls,
                         label=algo, dashes=dashes[i] or (None,None))
        self._style_ax(ax1, "Runtime (seconds) — log scale", "Seconds (log)", labels)

        # ── Chart 2: Nodes ──
        ax2 = fig.add_subplot(gs[0, 1])
        for i, algo in enumerate(algos):
            vals = [max(d[algo][1], 0.5) for d in data]
            ax2.semilogy(idx, vals, color=colors[i], marker=markers[i],
                         markersize=5, linewidth=1.8,
                         linestyle="--" if dashes[i] else "-",
                         dashes=dashes[i] or (None,None), label=algo)
        self._style_ax(ax2, "Nodes Expanded — log scale", "Nodes (log)", labels)

        # ── Chart 3: RAM ──
        ax3 = fig.add_subplot(gs[1, 0])
        for i, algo in enumerate(algos):
            vals = [d[algo][2] for d in data]
            ax3.plot(idx, vals, color=colors[i], marker=markers[i],
                     markersize=5, linewidth=1.8,
                     linestyle="--" if dashes[i] else "-",
                     dashes=dashes[i] or (None,None), label=algo)
        self._style_ax(ax3, "Peak RAM (MB) — linear", "MB", labels)

        # ── Chart 4: Bar — Runtime tổng hợp nhóm ──
        ax4 = fig.add_subplot(gs[1, 1])
        x = np.arange(len(data))
        w = 0.18
        offsets = [-1.5, -0.5, 0.5, 1.5]
        for i, algo in enumerate(algos):
            vals = [d[algo][0] for d in data]
            bars = ax4.bar(x + offsets[i]*w, vals, width=w,
                           color=colors[i], alpha=0.85, label=algo)
        ax4.set_yscale("log")
        self._style_ax(ax4, "Runtime comparison — grouped bar", "Seconds (log)", labels)

        # Legend chung
        handles, lbl = ax1.get_legend_handles_labels()
        fig.legend(handles, lbl, loc="upper center", ncol=4,
                   frameon=False, fontsize=9,
                   labelcolor=[THEME["bt_color"],THEME["fc_color"],
                                THEME["bc_color"],THEME["as_color"]])

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _style_ax(self, ax, title, ylabel, xlabels):
        ax.set_facecolor(THEME["surface"])
        ax.set_title(title, color=THEME["text_muted"], fontsize=9, pad=8)
        ax.set_ylabel(ylabel, color=THEME["text_dim"], fontsize=8)
        ax.set_xticks(range(len(xlabels)))
        ax.set_xticklabels(xlabels, fontsize=7.5, color=THEME["text_dim"], rotation=35)
        ax.tick_params(colors=THEME["text_dim"], labelsize=7.5)
        ax.grid(True, color=THEME["border"], alpha=0.5, linewidth=0.5)
        for spine in ax.spines.values():
            spine.set_color(THEME["border"])

    def _build_table(self):
        # Scrollable table
        container = tk.Frame(self.table_frame, bg=THEME["bg"])
        container.pack(fill="both", expand=True, padx=10, pady=10)

        canvas = tk.Canvas(container, bg=THEME["bg"], highlightthickness=0)
        vsb = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        hsb = tk.Scrollbar(container, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=THEME["bg"])
        canvas.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Header
        cols = ["File","N","Nghiệm",
                "BT T(s)","BT Nodes","BT RAM",
                "FC T(s)","FC Nodes","FC RAM",
                "BC T(s)","BC Inf.","BC RAM",
                "A* T(s)","A* Nodes","A* RAM",
                "Winner"]
        col_w = [90,40,75, 80,80,65, 80,80,65, 80,65,65, 80,80,65, 65]

        for ci, (col, w) in enumerate(zip(cols, col_w)):
            algo = col.split()[0] if col.split()[0] in ALGO_COLORS else None
            fg = ALGO_COLORS.get(algo, THEME["text_dim"])
            tk.Label(inner, text=col, font=("Consolas",9,"bold"),
                     bg=THEME["surface2"], fg=fg,
                     width=w//7, relief="flat", pady=8, padx=4,
                     anchor="center").grid(row=0, column=ci, padx=1, pady=1, sticky="nsew")

        for ri, d in enumerate(BENCHMARK_DATA):
            row_bg = THEME["surface"] if ri % 2 == 0 else THEME["surface2"]

            # Winner
            times = {"BT": d["BT"][0], "FC": d["FC"][0], "A*": d["A*"][0]}
            winner = min(times, key=times.get)
            winner_color = ALGO_COLORS[winner]

            sol_text = "✓ Có nghiệm" if d["sol"] else "✗ Vô nghiệm"
            sol_color = THEME["green"] if d["sol"] else THEME["red"]

            vals = [
                (d["file"], THEME["text"]),
                (f"{d['N']}×{d['N']}", THEME["text_muted"]),
                (sol_text, sol_color),
                (f"{d['BT'][0]:.4f}", THEME["bt_color"]),
                (f"{d['BT'][1]:,}", THEME["bt_color"]),
                (f"{d['BT'][2]:.3f}", THEME["bt_color"]),
                (f"{d['FC'][0]:.4f}", THEME["fc_color"]),
                (f"{d['FC'][1]:,}", THEME["fc_color"]),
                (f"{d['FC'][2]:.3f}", THEME["fc_color"]),
                (f"{d['BC'][0]:.4f}", THEME["bc_color"]),
                (f"{d['BC'][1]:,}", THEME["bc_color"]),
                (f"{d['BC'][2]:.3f}", THEME["bc_color"]),
                (f"{d['A*'][0]:.4f}", THEME["as_color"]),
                (f"{d['A*'][1]:,}", THEME["as_color"]),
                (f"{d['A*'][2]:.3f}", THEME["as_color"]),
                (winner, winner_color),
            ]
            for ci, ((text, color), w) in enumerate(zip(vals, col_w)):
                font = ("Consolas", 9, "bold") if ci == len(vals)-1 else ("Consolas", 9)
                tk.Label(inner, text=text, font=font,
                         bg=row_bg, fg=color,
                         width=w//7, relief="flat", pady=6, padx=4,
                         anchor="center").grid(row=ri+1, column=ci, padx=1, pady=0, sticky="nsew")

        # Footer note
        note = ("* BC chỉ đo suy diễn 1 ô mồi — không phải solver hoàn chỉnh.  "
                "Input-06 & Input-08: bảng vô nghiệm.  "
                "Đo bằng tracemalloc (RAM) và time.perf_counter() (time).")
        tk.Label(self.table_frame, text=note, font=FONT_SMALL,
                 bg=THEME["bg"], fg=THEME["text_dim"],
                 wraplength=900, justify="left").pack(padx=10, pady=(4,10), anchor="w")

    def _rerun(self):
        messagebox.showinfo("Re-run Benchmark",
                            "Tính năng này sẽ chạy lại toàn bộ 10 test cases và cập nhật biểu đồ.\n"
                            "Vui lòng dùng tab Solver để chạy từng file hoặc chạy futoshiki.py từ terminal để benchmark đầy đủ.")


# ═══════════════════════════════════════════════════════════════════════════════
# APP CHÍNH
# ═══════════════════════════════════════════════════════════════════════════════

class FutoshikiApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Futoshiki Solver — Algorithm Visualizer")
        self.geometry("1180x820")
        self.minsize(900, 650)
        self.configure(bg=THEME["bg"])
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._apply_ttk_style()
        self._build_ui()

    def _on_closing(self):
        try:
            # Ép cờ dừng (stop_flag) thành True để ngắt ngay lập tức các thuật toán đang chạy
            if hasattr(self, 'solver_tab'):
                self.solver_tab.stop_flag[0] = True
                self.solver_tab.running = False
        except Exception:
            pass
        
        self.destroy()   # Đóng giao diện an toàn
        os._exit(0)  # Force exit để đảm bảo tất cả threads con bị dừng

    def _apply_ttk_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook",
                        background=THEME["bg"], borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=THEME["surface2"], foreground=THEME["text_muted"],
                        font=("Consolas", 11), padding=[16, 8],
                        borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", THEME["surface"]),
                               ("active",   THEME["surface3"])],
                  foreground=[("selected", THEME["accent"]),
                               ("active",   THEME["text"])])

    def _build_ui(self):
        # Title bar
        title_bar = tk.Frame(self, bg=THEME["surface"], height=48)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        tk.Label(title_bar, text="◈  FUTOSHIKI ALGORITHM VISUALIZER",
                 font=("Consolas", 13, "bold"),
                 bg=THEME["surface"], fg=THEME["accent"]).pack(side="left", padx=20, pady=12)

        tk.Label(title_bar,
                 text="BT · FC/DPLL · BC · A*+MRV",
                 font=FONT_SMALL,
                 bg=THEME["surface"], fg=THEME["text_dim"]).pack(side="right", padx=20)

        # Tabs
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        self.solver_tab = SolverTab(nb)
        self.bench_tab  = BenchmarkTab(nb)
        nb.add(self.solver_tab, text="  🎯 Solver  ")
        nb.add(self.bench_tab,  text="  📊 Benchmark  ")

        # Status bar
        self.status = tk.Label(self, text="Ready — Mở file input để bắt đầu",
                                font=FONT_SMALL, bg=THEME["surface"],
                                fg=THEME["text_dim"], anchor="w", padx=16, pady=5)
        self.status.pack(fill="x", side="bottom")


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = FutoshikiApp()
    app.mainloop()