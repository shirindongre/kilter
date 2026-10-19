"""The three Phase 1 figures, drawn from results/summary.json (blueprint 5.3).

Design (dataviz skill): three arms use categorical slots 1-3 in fixed order (A3 blue, A1 orange, A4 aqua), validated
all-pairs in light mode (CVD dE 9.2, normal-vision dE 24.0). Aqua is below 3:1 on the surface, so the relief rule
applies: every figure carries a legend plus direct labels, and results_table.md is the table view. Bars are thin
with a surface-coloured gap, whiskers are exact binomial 95% intervals, grids are hairline, text never wears a
series colour.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "results" / "figures"

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"
COLOR = {"A3": "#2a78d6", "A1": "#eb6834", "A4": "#1baf7a"}
NAME = {"A3": "A3  T0+T1+T2", "A1": "A1  LLM self-critique", "A4": "A4  T0+T1 only"}
ORDER = ("A3", "A1", "A4")


def _style(ax, grid_axis="y"):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, length=0, labelsize=9)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _fig(w, h):
    fig = plt.figure(figsize=(w, h), dpi=160, facecolor=SURFACE)
    return fig


def fig_detection_by_class(S: dict) -> Path:
    main, hold = S["main"]["arms"], S["holdout"]["arms"]
    groups = [(c, "main", c) for c in ("D1", "D2", "D3", "D4", "D5")] + [("D5", "holdout", "D5 subtle\n(holdout)")]
    fig = _fig(10, 4.6)
    ax = fig.add_axes([0.07, 0.17, 0.91, 0.66])
    _style(ax)
    bw = 0.2
    xs = [0, 1, 2, 3, 4, 5.4]
    for j, arm in enumerate(ORDER):
        for x, (cls, which, _) in zip(xs, groups):
            c = (main if which == "main" else hold)[arm]["per_class"][cls]
            xp = x + (j - 1) * (bw + 0.03)
            ax.bar(xp, c["rate"], width=bw, color=COLOR[arm], edgecolor=SURFACE, linewidth=1.5, zorder=3)
            ax.plot([xp, xp], [c["lo"], c["hi"]], color=INK2, linewidth=1.0, zorder=4)
            if cls == "D5":  # selective labels: only the class where the architecture is decided
                ax.text(xp, min(c["hi"], 1.0) + 0.025, f"{c['k']}/{c['n']}", ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks(xs, [g[2] for g in groups], fontsize=9, color=INK)
    ax.set_ylim(0, 1.14)
    ax.set_yticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"])
    ax.axvline(4.7, color=GRID, linewidth=0.8)
    fig.text(0.07, 0.93, "Detection of planted defects, by class and arm", fontsize=13, color=INK, fontweight="bold")
    fig.text(0.07, 0.885, "Whiskers: exact 95% binomial interval. 8 variants per class. Holdout = subtler overclaims, reported separately.",
             fontsize=9, color=INK2)
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLOR[a]) for a in ORDER]
    fig.legend(handles, [NAME[a] for a in ORDER], loc="lower left", bbox_to_anchor=(0.07, 0.0), ncol=3, frameon=False,
               fontsize=9, labelcolor=INK2)
    p = OUT / "fig1_detection_by_class.png"
    fig.savefig(p, facecolor=SURFACE)
    plt.close(fig)
    return p


def fig_fpr_vs_detection(S: dict) -> Path:
    # A scatter is the wrong form here: every false-positive rate is 0/8, so one axis is degenerate. A paired forest
    # plot shows both quantities with their exact intervals, and makes the real message visible: 0/8 only bounds
    # the false-positive rate below ~37%.
    rows = [(which, arm) for which in ("main", "holdout") for arm in ("A3", "A4", "A1", "A0")]
    ys = [i + (0.7 if which == "holdout" else 0) for i, (which, _) in enumerate(rows)]
    fig = _fig(10, 5.4)
    axd = fig.add_axes([0.2, 0.12, 0.36, 0.70])
    axf = fig.add_axes([0.62, 0.12, 0.34, 0.70])
    for ax in (axd, axf):
        _style(ax, "x")
        ax.set_ylim(max(ys) + 0.7, -0.7)
        ax.set_xlim(-0.02, 1.02)
        ax.set_xticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"])
    axd.set_xlim(-0.02, 1.16)  # room for the count column
    axf.set_xlim(-0.02, 0.62)
    axf.set_xticks([0, .1, .2, .3, .4, .5], ["0%", "10%", "20%", "30%", "40%", "50%"])
    axf.set_yticks([])
    axd.set_yticks(ys, [f"{arm}   {'holdout' if w == 'holdout' else 'main'}" for w, arm in rows], fontsize=9, color=INK)
    for y, (which, arm) in zip(ys, rows):
        a = S[which]["arms"][arm]
        colour = COLOR.get(arm, MUTED)
        for ax, c, label_x in ((axd, a["overall_detection"], 1.05), (axf, a["per_class"]["clean"], 0.45)):
            ax.plot([c["lo"], c["hi"]], [y, y], color=INK2, linewidth=1.2, zorder=2)
            ax.scatter([c["rate"]], [y], s=64, color=colour, edgecolor=SURFACE, linewidth=2, zorder=5)
            ax.text(label_x, y, f"{c['k']}/{c['n']}", va="center", fontsize=8.5, color=INK)  # fixed column: never on a mark
    axd.set_title("Detection of planted defects (higher is better)", fontsize=9.5, color=INK2, loc="left")
    axf.set_title("False positives on clean analyses (lower is better)", fontsize=9.5, color=INK2, loc="left")
    fig.text(0.04, 0.93, "Detection and false positives, with exact 95% intervals", fontsize=13, color=INK, fontweight="bold")
    fig.text(0.04, 0.885, "Zero false positives in 8 clean analyses still allows a true rate of up to about 37%. A0 = no verification.",
             fontsize=9, color=INK2)
    handles = [plt.Line2D([], [], marker="o", linestyle="", color=COLOR.get(a, MUTED), markersize=8) for a in ("A3", "A1", "A4", "A0")]
    fig.legend(handles, [NAME.get(a, "A0  no verification") for a in ("A3", "A1", "A4", "A0")], loc="lower left",
               bbox_to_anchor=(0.04, 0.0), ncol=4, frameon=False, fontsize=9, labelcolor=INK2)
    p = OUT / "fig2_fpr_vs_detection.png"
    fig.savefig(p, facecolor=SURFACE)
    plt.close(fig)
    return p


def fig_cost_matched(S: dict) -> Path:
    fig = _fig(10, 4.6)
    ax1 = fig.add_axes([0.06, 0.17, 0.26, 0.64])
    ax2 = fig.add_axes([0.42, 0.17, 0.55, 0.64])
    _style(ax1, "x")
    _style(ax2)
    cost = {a: S["main"]["arms"][a]["cost"] for a in ORDER}
    for i, arm in enumerate(ORDER):
        v = cost[arm]["input_tokens_mean"] + cost[arm]["output_tokens_billed_mean"]
        ax1.barh(i, v, height=0.34, color=COLOR[arm], edgecolor=SURFACE, linewidth=1.5, zorder=3)
        ax1.text(v + 60, i, f"{v:,.0f}" if v else "0", va="center", fontsize=9, color=INK)
    ax1.set_yticks(range(3), [NAME[a].split("  ")[0] for a in ORDER], fontsize=10, color=INK)
    ax1.invert_yaxis()
    ax1.set_xlim(0, max(cost[a]["input_tokens_mean"] + cost[a]["output_tokens_billed_mean"] for a in ORDER) * 1.3)
    ax1.set_xticks([])
    ax1.set_title("Tokens per audit (input + billed output)", fontsize=9.5, color=INK2, loc="left")
    bw = 0.2
    for j, arm in enumerate(ORDER):
        for x, which in ((0, "main"), (1.4, "holdout")):
            c = S[which]["arms"][arm]["per_class"]["D5"]
            xp = x + (j - 1) * (bw + 0.03)
            ax2.bar(xp, c["rate"], width=bw, color=COLOR[arm], edgecolor=SURFACE, linewidth=1.5, zorder=3)
            ax2.plot([xp, xp], [c["lo"], c["hi"]], color=INK2, linewidth=1.0, zorder=4)
            ax2.text(xp, min(c["hi"], 1.0) + 0.025, f"{c['k']}/{c['n']}", ha="center", fontsize=8, color=INK)
    ax2.set_xticks([0, 1.4], ["D5 overclaim: blatant (main)", "D5 overclaim: subtle (holdout)"], fontsize=9, color=INK)
    ax2.set_ylim(0, 1.14)
    ax2.set_yticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"])
    ax2.set_title("Detection of the class with no sound check", fontsize=9.5, color=INK2, loc="left")
    fig.text(0.06, 0.93, "What the LLM tier buys, and what it costs", fontsize=13, color=INK, fontweight="bold")
    fig.text(0.06, 0.885, "A3 spends about half of A1's tokens. A4 spends none. Whiskers: exact 95% binomial interval.", fontsize=9, color=INK2)
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLOR[a]) for a in ORDER]
    fig.legend(handles, [NAME[a] for a in ORDER], loc="lower left", bbox_to_anchor=(0.06, 0.0), ncol=3, frameon=False,
               fontsize=9, labelcolor=INK2)
    p = OUT / "fig3_cost_matched_a3_vs_a4.png"
    fig.savefig(p, facecolor=SURFACE)
    plt.close(fig)
    return p


def build_figures() -> list[Path]:
    S = json.loads((ROOT / "results" / "summary.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    return [fig_detection_by_class(S), fig_fpr_vs_detection(S), fig_cost_matched(S)]


if __name__ == "__main__":
    for p in build_figures():
        print(p)
