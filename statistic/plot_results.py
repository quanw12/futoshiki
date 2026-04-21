"""
Plot benchmark results (headless, no UI).
Style, theme, and plotting libraries match `ref/futoshiki_ui.py` (matplotlib + numpy).
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np


THEME = {
    "bg": "#FFFFFF",
    "surface": "#FFFFFF",
    "surface2": "#F8FAFC",
    "surface3": "#F1F5F9",
    "accent": "#1D4ED8",
    "accent2": "#6D28D9",
    "green": "#047857",
    "yellow": "#B45309",
    "red": "#B91C1C",
    "text": "#0B1220",
    "text_muted": "#334155",
    "text_dim": "#475569",
    "border": "#CBD5E1",
    "bt_color": "#B91C1C",
    "fc_color": "#B45309",
    "bc_color": "#6D28D9",
    "as_color": "#047857",
}


ALGO_COLORS = {
    "backtracking": THEME["bt_color"],
    "forward": THEME["fc_color"],
    "backward": THEME["bc_color"],
    "astar": THEME["as_color"],
    "bruteforce": THEME["text_muted"],
}


@dataclass(frozen=True)
class ResultRow:
    algorithm_name: str
    test_case_id: str
    solution_steps: int
    execution_time_ms: float
    nodes_expanded: int


def _read_csv(path: str) -> List[ResultRow]:
    rows: List[ResultRow] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for d in r:
            rows.append(
                ResultRow(
                    algorithm_name=d["Algorithm"],
                    test_case_id=d["TestCase"],
                    solution_steps=int(d["SolutionSteps"]),
                    execution_time_ms=float(d["ExecutionTime(ms)"]),
                    nodes_expanded=int(d["NodesExpanded"]),
                )
            )
    return rows


def _style_ax(ax, title: str, ylabel: str, xlabels: Sequence[str]) -> None:
    ax.set_facecolor(THEME["surface"])
    ax.set_title(title, color=THEME["text"], fontsize=10, pad=10)
    ax.set_ylabel(ylabel, color=THEME["text_muted"], fontsize=9)
    ax.set_xticks(range(len(xlabels)))
    ax.set_xticklabels(xlabels, fontsize=8, color=THEME["text_dim"], rotation=35)
    ax.tick_params(colors=THEME["text_dim"], labelsize=8)
    ax.grid(True, axis="y", color=THEME["border"], alpha=0.9, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_color(THEME["border"])
        spine.set_linewidth(0.8)


def _group(rows: Sequence[ResultRow]) -> Tuple[List[str], List[str], Dict[Tuple[str, str], ResultRow]]:
    algos = sorted({r.algorithm_name for r in rows})
    cases = sorted({r.test_case_id for r in rows})
    m: Dict[Tuple[str, str], ResultRow] = {(r.algorithm_name, r.test_case_id): r for r in rows}
    return algos, cases, m


def _labels_for_cases(cases: Sequence[str]) -> List[str]:
    out: List[str] = []
    for tc in cases:
        s = tc.replace("input-", "").replace("input_", "").replace("input", "")
        out.append(f"#{s}" if s else tc)
    return out


def _metric_matrix(
    algos: Sequence[str],
    cases: Sequence[str],
    m: Dict[Tuple[str, str], ResultRow],
    metric: str,
) -> np.ndarray:
    arr = np.zeros((len(algos), len(cases)), dtype=float)
    for i, a in enumerate(algos):
        for j, c in enumerate(cases):
            r = m[(a, c)]
            if metric == "time":
                arr[i, j] = r.execution_time_ms
            elif metric == "nodes":
                arr[i, j] = r.nodes_expanded
            elif metric == "steps":
                arr[i, j] = r.solution_steps
            else:
                raise ValueError(metric)
    return arr


def _plot_per_case(
    out_path: str,
    title: str,
    ylabel: str,
    algos: Sequence[str],
    cases: Sequence[str],
    values: np.ndarray,
    logy: bool,
) -> None:
    plt.style.use("default")
    fig = plt.figure(figsize=(13, 6), facecolor=THEME["bg"])
    gs = gridspec.GridSpec(
        1,
        1,
        figure=fig,
        left=0.07,
        right=0.97,
        top=0.90,
        bottom=0.18,
    )
    ax = fig.add_subplot(gs[0, 0])
    idx = np.arange(len(cases))
    w = 0.8 / max(len(algos), 1)
    offsets = (np.arange(len(algos)) - (len(algos) - 1) / 2.0) * w

    for i, algo in enumerate(algos):
        color = ALGO_COLORS.get(algo, THEME["text_muted"])
        ax.bar(idx + offsets[i], values[i], width=w, color=color, alpha=0.85, edgecolor=THEME["border"], linewidth=0.6, label=algo)

    if logy:
        ax.set_yscale("log")
    _style_ax(ax, title, ylabel, _labels_for_cases(cases))
    handles, lbl = ax.get_legend_handles_labels()
    fig.legend(
        handles,
        lbl,
        loc="upper center",
        ncol=min(6, max(1, len(algos))),
        frameon=True,
        fontsize=9,
        edgecolor=THEME["border"],
        facecolor=THEME["surface2"],
    )

    fig.savefig(out_path, dpi=180, facecolor=THEME["bg"])
    plt.close(fig)


def _plot_overall(
    out_path: str,
    algos: Sequence[str],
    values_time: np.ndarray,
    values_nodes: np.ndarray,
    values_steps: np.ndarray,
) -> None:
    avg_time = values_time.mean(axis=1)
    avg_nodes = values_nodes.mean(axis=1)
    avg_steps = values_steps.mean(axis=1)

    x = np.arange(len(algos))
    colors = [ALGO_COLORS.get(a, THEME["text_muted"]) for a in algos]

    # Chart 1: avg time (ms)
    plt.style.use("default")
    fig1 = plt.figure(figsize=(10, 5), facecolor=THEME["bg"])
    ax1 = fig1.add_subplot(1, 1, 1)
    ax1.bar(x, avg_time, color=colors, alpha=0.85, edgecolor=THEME["border"], linewidth=0.6)
    ax1.set_yscale("log")
    _style_ax(ax1, "Average Execution Time (ms) — log scale", "ms (log)", algos)
    ax1.set_xticklabels(algos, fontsize=9, color=THEME["text_dim"], rotation=0)
    fig1.savefig(out_path.replace(".png", "_avg_time.png"), dpi=180, facecolor=THEME["bg"])
    plt.close(fig1)

    # Chart 2: avg nodes
    fig2 = plt.figure(figsize=(10, 5), facecolor=THEME["bg"])
    ax2 = fig2.add_subplot(1, 1, 1)
    ax2.bar(x, avg_nodes, color=colors, alpha=0.85, edgecolor=THEME["border"], linewidth=0.6)
    ax2.set_yscale("log")
    _style_ax(ax2, "Average Nodes Expanded — log scale", "nodes (log)", algos)
    ax2.set_xticklabels(algos, fontsize=9, color=THEME["text_dim"], rotation=0)
    fig2.savefig(out_path.replace(".png", "_avg_nodes.png"), dpi=180, facecolor=THEME["bg"])
    plt.close(fig2)

    # Chart 3: avg steps
    fig3 = plt.figure(figsize=(10, 5), facecolor=THEME["bg"])
    ax3 = fig3.add_subplot(1, 1, 1)
    ax3.bar(x, avg_steps, color=colors, alpha=0.85, edgecolor=THEME["border"], linewidth=0.6)
    _style_ax(ax3, "Average Solution Steps — linear", "steps", algos)
    ax3.set_xticklabels(algos, fontsize=9, color=THEME["text_dim"], rotation=0)
    fig3.savefig(out_path.replace(".png", "_avg_steps.png"), dpi=180, facecolor=THEME["bg"])
    plt.close(fig3)

    # Chart 4: combined comparison
    fig4 = plt.figure(figsize=(10, 5), facecolor=THEME["bg"])
    ax4 = fig4.add_subplot(1, 1, 1)
    w = 0.25
    ax4.bar(
        x - w,
        avg_time,
        width=w,
        color=THEME["accent"],
        alpha=0.85,
        edgecolor=THEME["border"],
        linewidth=0.6,
        label="Time (ms)",
    )
    ax4.bar(
        x,
        avg_nodes,
        width=w,
        color=THEME["green"],
        alpha=0.85,
        edgecolor=THEME["border"],
        linewidth=0.6,
        label="Nodes",
    )
    ax4.bar(
        x + w,
        avg_steps,
        width=w,
        color=THEME["yellow"],
        alpha=0.85,
        edgecolor=THEME["border"],
        linewidth=0.6,
        label="Steps",
    )
    ax4.set_yscale("log")
    _style_ax(ax4, "Overall Comparison (averages) — log scale", "value (log)", algos)
    ax4.set_xticklabels(algos, fontsize=9, color=THEME["text_dim"], rotation=0)
    ax4.legend(frameon=True, fontsize=9, edgecolor=THEME["border"], facecolor=THEME["surface2"])
    fig4.savefig(out_path.replace(".png", "_comparison.png"), dpi=180, facecolor=THEME["bg"])
    plt.close(fig4)


def main() -> None:
    repo_root = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(repo_root, "benchmark_results.csv")
    rows = _read_csv(csv_path)

    algos, cases, m = _group(rows)
    time_m = _metric_matrix(algos, cases, m, "time")
    nodes_m = _metric_matrix(algos, cases, m, "nodes")
    steps_m = _metric_matrix(algos, cases, m, "steps")

    _plot_per_case(
        os.path.join(repo_root, "execution_time_per_testcase.png"),
        "Execution Time per Test Case — grouped bar",
        "ExecutionTime(ms)",
        algos,
        cases,
        time_m,
        logy=True,
    )
    _plot_per_case(
        os.path.join(repo_root, "nodes_expanded_per_testcase.png"),
        "Nodes Expanded per Test Case — grouped bar",
        "NodesExpanded",
        algos,
        cases,
        nodes_m,
        logy=True,
    )
    _plot_per_case(
        os.path.join(repo_root, "solution_steps_per_testcase.png"),
        "Solution Steps per Test Case — grouped bar",
        "SolutionSteps",
        algos,
        cases,
        steps_m,
        logy=False,
    )
    _plot_overall(
        os.path.join(repo_root, "overall_comparison.png"),
        algos,
        time_m,
        nodes_m,
        steps_m,
    )


if __name__ == "__main__":
    main()

