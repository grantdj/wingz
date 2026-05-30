#!/usr/bin/env python3
"""
Formation drag analysis: drag reduction by position, geometry, and overlap.

Usage:
    .venv/bin/python scripts/formation_drag_analysis.py
    .venv/bin/python scripts/formation_drag_analysis.py --save
"""

import sys
import os
import numpy as np
import matplotlib

SAVE = "--save" in sys.argv
if SAVE:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from wingz.aerodynamics.formation_aero import per_slot_drag_factor, effective_span, FormationGeometry


def _draw_mini_formation(ax_inset, geo, N, span=1.0):
    """Draw a small top-down formation diagram with numbered slots."""
    overlap = 0.1
    gap = span * (1 - overlap)
    sep = span * 1.5

    if geo == FormationGeometry.V:
        positions = [(0, 0)]
        depth = 1; idx = 1
        while idx < N:
            x = depth * gap; y = -depth * sep
            positions.append((-x, y)); idx += 1
            if idx < N:
                positions.append((x, y)); idx += 1
            depth += 1
    elif geo == FormationGeometry.ECHELON:
        positions = [(i * gap, -i * sep) for i in range(N)]
    else:  # inline
        positions = [(0, -i * sep) for i in range(N)]

    cmap = plt.cm.RdYlGn
    factors = per_slot_drag_factor(N, span, overlap, geo)

    for i, (x, y) in enumerate(positions):
        color = cmap(1 - factors[i])
        ax_inset.plot([x - span / 2, x + span / 2], [y, y],
                      color=color, lw=2.5, solid_capstyle='round')
        ax_inset.text(x, y + sep * 0.25, str(i), ha='center', va='center',
                      fontsize=7, fontweight='bold',
                      bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='gray', alpha=0.8))

    ax_inset.set_aspect('equal')
    ax_inset.set_xlim(-N * gap, N * gap)
    pad = sep * 0.5
    ys = [p[1] for p in positions]
    ax_inset.set_ylim(min(ys) - pad, max(ys) + pad * 2)
    ax_inset.axis('off')


def main():
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))

    span = 20
    overlap = 0.1
    N_show = 5  # N for the inset diagrams

    # Top row: drag reduction per slot with inset formation diagrams
    for idx, geo in enumerate([FormationGeometry.V, FormationGeometry.ECHELON, FormationGeometry.INLINE]):
        ax = axes[0, idx]

        for N in [2, 3, 4, 5, 6, 8]:
            factors = per_slot_drag_factor(N, span, overlap, geo)
            reductions = [(1 - f) * 100 for f in factors]
            ax.bar([s + (N - 2) * 0.12 for s in range(N)], reductions,
                   width=0.1, label=f"N={N}", alpha=0.8)

        ax.set_xlabel("Slot position (0 = leader)")
        ax.set_ylabel("Drag reduction (%)")
        ax.set_title(f"{geo.value.upper()} Formation")
        ax.legend(fontsize=7, ncol=2, loc='upper left')
        ax.grid(True, alpha=0.3, axis="y")
        ax.set_ylim(0, 80)

        # Inset diagram showing slot positions
        ax_inset = inset_axes(ax, width="30%", height="45%", loc='upper right',
                              borderpad=1.5)
        _draw_mini_formation(ax_inset, geo, N_show)

    # Bottom left: effective span vs N
    ax = axes[1, 0]
    Ns = range(1, 11)
    for geo, color, ls in [
        (FormationGeometry.V, "tab:blue", "-"),
        (FormationGeometry.ECHELON, "tab:orange", "--"),
        (FormationGeometry.INLINE, "tab:green", ":"),
    ]:
        b_effs = [effective_span(N, span, overlap, geo) for N in Ns]
        ax.plot(list(Ns), b_effs, color=color, ls=ls, lw=2, marker="o",
                markersize=5, label=geo.value)
    ax.plot(list(Ns), [N * span for N in Ns], "k--", alpha=0.3,
            label="N*span (max)")
    ax.set_xlabel("Number of aircraft (N)")
    ax.set_ylabel("Effective span (m)")
    ax.set_title(f"Effective Span vs Fleet Size (span={span}m, overlap=10%)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Bottom middle: overlap sweep
    ax = axes[1, 1]
    overlaps = np.linspace(-0.2, 0.4, 50)
    for N in [2, 3, 4, 6]:
        b_effs = [effective_span(N, 20, ov, FormationGeometry.V) for ov in overlaps]
        ax.plot(overlaps * 100, b_effs, lw=2, label=f"N={N}")
    ax.axvline(10, color="red", ls="--", alpha=0.5, label="Optimal (10%)")
    ax.set_xlabel("Lateral overlap ratio (%)")
    ax.set_ylabel("Effective span (m)")
    ax.set_title("Effective Span vs Overlap (V formation, span=20m)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Bottom right: large top-down view with detail
    ax = axes[1, 2]
    N = 5
    gap = span * (1 - overlap)
    streamwise = span * 2

    positions = [(0, 0)]
    depth = 1; i = 1
    while i < N:
        x = depth * gap; y = -depth * streamwise
        positions.append((-x, y)); i += 1
        if i < N:
            positions.append((x, y)); i += 1
        depth += 1

    factors = per_slot_drag_factor(N, span, overlap, FormationGeometry.V)
    cmap = plt.cm.RdYlGn

    for i, (x, y) in enumerate(positions):
        color = cmap(1 - factors[i])
        ax.plot([x - span / 2, x + span / 2], [y, y], color=color, lw=4)
        ax.plot(x, y, "ko", markersize=4)
        red = (1 - factors[i]) * 100
        if i == 0:
            label = f"0: Leader\n0% reduction"
        else:
            label = f"{i}: F{i}\n-{red:.0f}%"
        ax.annotate(label, (x, y),
                    textcoords="offset points", xytext=(0, 14),
                    ha="center", fontsize=9, fontweight="bold",
                    bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='gray', alpha=0.8))

        # Wake arrows from wingtips
        ax.annotate("", xy=(x - span / 2 - 3, y - streamwise * 0.8),
                    xytext=(x - span / 2, y),
                    arrowprops=dict(arrowstyle="->", color="gray", alpha=0.3, lw=1))
        ax.annotate("", xy=(x + span / 2 + 3, y - streamwise * 0.8),
                    xytext=(x + span / 2, y),
                    arrowprops=dict(arrowstyle="->", color="gray", alpha=0.3, lw=1))

    ax.set_aspect("equal")
    ax.set_xlabel("Lateral position (m)")
    ax.set_ylabel("Streamwise position (m)")
    ax.set_title(f"V Formation — N={N}, span={span}m, 10% overlap\n"
                 "Color: green=low drag, red=full drag")
    ax.grid(True, alpha=0.2)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 100))
    sm.set_array([])
    plt.colorbar(sm, ax=ax, label="Drag reduction (%)")

    plt.suptitle("Formation Aerodynamics: Drag Reduction by Position, Geometry, and Overlap",
                 fontsize=14, y=1.02)
    plt.tight_layout()

    if SAVE:
        os.makedirs("docs/formation_flight", exist_ok=True)
        fig.savefig("docs/formation_flight/formation_drag_analysis.png",
                    dpi=150, bbox_inches="tight")
        print("Saved to docs/formation_flight/formation_drag_analysis.png")
    else:
        plt.show()


if __name__ == "__main__":
    main()
