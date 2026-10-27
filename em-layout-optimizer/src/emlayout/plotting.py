"""Whole-band plots for layout candidates.

One figure, two axes: drain/source efficiency on the left, output power on the
right. Curves are drawn straight from a results JSON, so re-plotting never
re-runs a solver.

Results format (one entry per candidate):

    {"candidate_a": [[f_GHz, pout_dBm, efficiency_pct], ...], ...}
"""
from __future__ import annotations

import json
import os
from typing import Iterable, Sequence


def load_results(path: str) -> dict[str, list[list[float]]]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def band(rows: Sequence[Sequence[float]], f_lo: float, f_hi: float) -> list[list[float]]:
    return [list(r) for r in rows if f_lo - 1e-9 <= r[0] <= f_hi + 1e-9]


def stats(rows: Sequence[Sequence[float]], f_lo: float, f_hi: float, target: float | None = None) -> dict:
    sel = band(rows, f_lo, f_hi)
    if not sel:
        return {}
    worst = min(sel, key=lambda r: r[2])
    return {
        "min_efficiency": worst[2],
        "min_freq": worst[0],
        "mean_efficiency": sum(r[2] for r in sel) / len(sel),
        "min_pout": min(r[1] for r in sel),
        "points": len(sel),
        "points_below_target": (sum(1 for r in sel if r[2] < target) if target is not None else None),
    }


def plot(results_path: str, out_stem: str, *, f_lo: float, f_hi: float,
         target: float | None = 60.0, title: str | None = None,
         labels: Iterable[str] | None = None) -> str:
    """Render DE/Pout for every candidate in the JSON; returns the PNG path."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = load_results(results_path)
    names = list(labels) if labels else list(data)
    colours = ["#1a73e8", "#d93025", "#188038", "#e37400", "#8e44ad", "#7f8c8d"]

    fig, ax = plt.subplots(figsize=(8.4, 5.0), dpi=170)
    ax2 = ax.twinx()
    for i, name in enumerate(names):
        rows = band(data[name], f_lo, f_hi)
        if not rows:
            continue
        c = colours[i % len(colours)]
        f = [r[0] for r in rows]
        eff = [r[2] for r in rows]
        pout = [r[1] for r in rows]
        ax.plot(f, eff, "-o", lw=1.8, ms=3.4, color=c,
                label=f"{name}  (min {min(eff):.1f}%)")
        ax2.plot(f, pout, "--", lw=1.0, alpha=0.5, color=c, label=f"{name}  Pout")

    if target is not None:
        ax.axhline(target, color="#188038", ls=":", lw=1.3)
        ax.text(f_lo + 0.005, target + 0.25, f"{target:.0f}% target",
                color="#188038", fontsize=8.5)

    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel("Efficiency (%)")
    ax2.set_ylabel("Output power (dBm)")
    ax.set_title(title or "Whole-band comparison")
    ax.grid(alpha=0.3)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7.5, loc="lower left", ncol=2)
    plt.tight_layout()

    os.makedirs(os.path.dirname(out_stem) or ".", exist_ok=True)
    for ext in ("png", "svg"):
        plt.savefig(f"{out_stem}.{ext}", bbox_inches="tight")
    plt.close(fig)
    return out_stem + ".png"