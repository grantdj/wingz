#!/usr/bin/env python3
"""
Design space search: brute-force grid sweep over all formation parameters.

Evaluates every combination, reports Pareto-optimal designs on the
(cost, payload) frontier, and flags unexpected sweet spots.

Usage:
    .venv/bin/python scripts/design_search.py
    .venv/bin/python scripts/design_search.py --save
"""

import sys
import os
import time
import numpy as np
import matplotlib
from multiprocessing import Pool, cpu_count

SAVE = "--save" in sys.argv
if SAVE:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt

from wingz.evaluation.solver import find_max_payload
from wingz.constants import (
    BATTERY_ENERGY_DENSITY, PANEL_EFFICIENCY, CD0, PAYLOAD_SPECIFIC_MASS,
)


# ── Search grid ─────────────────────────────────────────────────────────

GRID = {
    "N":        [1, 2, 3, 4, 6],
    "span":     [10, 15, 20, 25, 30, 40, 50, 60],
    "AR":       [6, 8, 10, 12, 14, 16, 18, 20],
}

# For now: fixed at defaults. Uncomment to unlock.
# "cd0":      [0.020, 0.025, 0.028, 0.035],
# "batt_Wh_kg": [250, 400, 500],
# "panel_eff": [0.30, 0.38, 0.42],
# "pld_g_W":  [20, 50, 100],


def _eval_point(args):
    """Evaluate one grid point. Returns dict or None."""
    N, span, AR = args
    chord = span / AR
    if chord < 0.4 or chord > 8.0:  # unbuildable
        return None
    try:
        r = find_max_payload(N, span, AR=AR)
    except Exception:
        return None
    if r is None or r["payload_mass_total"] < 0.1:
        return None
    r["dpkg"] = r["cost"] / max(0.1, r["payload_mass_total"])
    return r


def pareto_2d(results, x_key, y_key, lower_better_x=True, lower_better_y=False):
    """Return Pareto-optimal points. Default: lower cost, higher payload."""
    pts = sorted(results, key=lambda r: r[x_key])
    if not lower_better_x:
        pts = pts[::-1]
    pareto = []
    best_y = -np.inf if not lower_better_y else np.inf
    for r in pts:
        if (not lower_better_y and r[y_key] > best_y) or \
           (lower_better_y and r[y_key] < best_y):
            pareto.append(r)
            best_y = r[y_key]
    return pareto


def main():
    # Build grid
    points = []
    for N in GRID["N"]:
        for span in GRID["span"]:
            for AR in GRID["AR"]:
                points.append((N, span, AR))

    print(f"Design search: {len(points)} grid points, {cpu_count()} cores")
    print(f"Grid: N={GRID['N']}, span={GRID['span']}, AR={GRID['AR']}")
    print()

    t0 = time.time()
    with Pool(processes=min(cpu_count(), 10)) as pool:
        raw = pool.map(_eval_point, points)
    elapsed = time.time() - t0

    results = [r for r in raw if r is not None]
    print(f"Completed in {elapsed:.1f}s — {len(results)} feasible out of {len(points)} points")
    print()

    if not results:
        print("No feasible designs found!")
        return

    # ── Pareto frontier: cost vs payload mass ──
    pareto = pareto_2d(results, "cost", "payload_mass_total")

    print("=" * 120)
    print("PARETO FRONTIER: Lowest cost for each payload level")
    print("=" * 120)
    print()
    print(f"{'Config':>12} {'AR':>5} {'Chord':>6} {'Pld(kg)':>8} {'PldPwr':>7} {'AC(kg)':>7} "
          f"{'Fleet':>7} {'PanCov':>7} {'Cost':>9} {'$/kg':>9}")
    print("-" * 100)
    for r in pareto:
        name = f"{r['N']}x{r['span']:.0f}m"
        print(f"{name:>12} {r['AR']:>5.1f} {r['chord']:>5.2f}m {r['payload_mass_total']:>8.1f} "
              f"{r['payload_power']:>7.0f} {r['ac_mass']:>7.1f} {r['fleet_mass']:>7.1f} "
              f"{r['panel_coverage']:>6.0%} {r['cost']/1e6:>8.2f}M "
              f"{r['dpkg']/1000:>8.1f}k")

    # ── Best $/kg at each fleet size ──
    print()
    print("=" * 120)
    print("BEST $/kg PAYLOAD BY FLEET SIZE")
    print("=" * 120)
    print()
    for N in GRID["N"]:
        subset = [r for r in results if r["N"] == N]
        if not subset:
            print(f"  N={N}: no feasible configs")
            continue
        best = min(subset, key=lambda r: r["dpkg"])
        name = f"{N}x{best['span']:.0f}m"
        print(f"  N={N}: {name} AR={best['AR']:.0f} chord={best['chord']:.2f}m "
              f"— ${best['dpkg']/1000:.1f}k/kg, {best['payload_mass_total']:.0f}kg payload, "
              f"${best['cost']/1e6:.2f}M, {best['panel_coverage']:.0%} panel")

    # ── Surprising results ──
    print()
    print("=" * 120)
    print("SURPRISE CHECK: Is there a config that beats the expected winner?")
    print("=" * 120)
    print()

    overall_best = min(results, key=lambda r: r["dpkg"])
    name = f"{overall_best['N']}x{overall_best['span']:.0f}m"
    print(f"Overall cheapest $/kg: {name} AR={overall_best['AR']:.0f} "
          f"— ${overall_best['dpkg']/1000:.1f}k/kg")
    print()

    # Check: do small formations ever beat large ones at the same payload level?
    print("Do small formations (N≤2) ever beat large ones (N≥4) at same payload?")
    for pld_level in [25, 50, 100, 200, 500]:
        small = [r for r in results if r["N"] <= 2 and r["payload_mass_total"] >= pld_level]
        large = [r for r in results if r["N"] >= 4 and r["payload_mass_total"] >= pld_level]
        if small and large:
            best_small = min(small, key=lambda r: r["cost"])
            best_large = min(large, key=lambda r: r["cost"])
            winner = "SMALL" if best_small["cost"] < best_large["cost"] else "LARGE"
            print(f"  ≥{pld_level}kg: small=${best_small['cost']/1e6:.2f}M "
                  f"({best_small['N']}x{best_small['span']:.0f}m) vs "
                  f"large=${best_large['cost']/1e6:.2f}M "
                  f"({best_large['N']}x{best_large['span']:.0f}m) → {winner} wins")

    # ── Plot ──
    fig, axes = plt.subplots(2, 3, figsize=(18, 11))
    fig.suptitle("Design Space Search — All Feasible Configurations", fontsize=14)

    colors_N = {1: "tab:blue", 2: "tab:orange", 3: "tab:green", 4: "tab:red", 6: "tab:purple"}

    # 1: Cost vs Payload Mass (Pareto)
    ax = axes[0, 0]
    for N in GRID["N"]:
        sub = [r for r in results if r["N"] == N]
        if sub:
            ax.scatter([r["payload_mass_total"] for r in sub],
                       [r["cost"]/1e6 for r in sub],
                       c=colors_N.get(N, "gray"), s=15, alpha=0.4, label=f"N={N}")
    ax.plot([r["payload_mass_total"] for r in pareto],
            [r["cost"]/1e6 for r in pareto],
            "k-o", lw=2, markersize=5, label="Pareto", zorder=5)
    ax.set_xlabel("Payload mass (kg)")
    ax.set_ylabel("Cost ($M)")
    ax.set_title("Cost vs Payload — Pareto Frontier")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 2: $/kg vs Span, colored by N
    ax = axes[0, 1]
    for N in GRID["N"]:
        sub = [r for r in results if r["N"] == N]
        if sub:
            ax.scatter([r["span"] for r in sub],
                       [r["dpkg"]/1000 for r in sub],
                       c=colors_N.get(N, "gray"), s=15, alpha=0.4, label=f"N={N}")
    ax.set_xlabel("Span per aircraft (m)")
    ax.set_ylabel("$/kg payload (thousands)")
    ax.set_title("$/kg vs Span")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, min(500, ax.get_ylim()[1]))

    # 3: $/kg vs AR, colored by N
    ax = axes[0, 2]
    for N in GRID["N"]:
        sub = [r for r in results if r["N"] == N]
        if sub:
            ax.scatter([r["AR"] for r in sub],
                       [r["dpkg"]/1000 for r in sub],
                       c=colors_N.get(N, "gray"), s=15, alpha=0.4, label=f"N={N}")
    ax.set_xlabel("Aspect Ratio")
    ax.set_ylabel("$/kg payload (thousands)")
    ax.set_title("$/kg vs AR")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, min(500, ax.get_ylim()[1]))

    # 4: Panel coverage vs payload
    ax = axes[1, 0]
    for N in GRID["N"]:
        sub = [r for r in results if r["N"] == N]
        if sub:
            ax.scatter([r["payload_mass_total"] for r in sub],
                       [r["panel_coverage"]*100 for r in sub],
                       c=colors_N.get(N, "gray"), s=15, alpha=0.4, label=f"N={N}")
    ax.set_xlabel("Payload mass (kg)")
    ax.set_ylabel("Panel coverage (%)")
    ax.set_title("Panel Coverage vs Payload")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 5: AC mass vs span, colored by N
    ax = axes[1, 1]
    for N in GRID["N"]:
        sub = [r for r in results if r["N"] == N]
        if sub:
            ax.scatter([r["span"] for r in sub],
                       [r["ac_mass"] for r in sub],
                       c=colors_N.get(N, "gray"), s=15, alpha=0.4, label=f"N={N}")
    ax.set_xlabel("Span per aircraft (m)")
    ax.set_ylabel("Per-aircraft mass (kg)")
    ax.set_title("Vehicle Mass vs Span")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 6: Chord vs $/kg — does minimum chord matter?
    ax = axes[1, 2]
    for N in GRID["N"]:
        sub = [r for r in results if r["N"] == N]
        if sub:
            ax.scatter([r["chord"] for r in sub],
                       [r["dpkg"]/1000 for r in sub],
                       c=colors_N.get(N, "gray"), s=15, alpha=0.4, label=f"N={N}")
    ax.set_xlabel("Chord (m)")
    ax.set_ylabel("$/kg payload (thousands)")
    ax.set_title("$/kg vs Chord")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, min(500, ax.get_ylim()[1]))

    plt.tight_layout()

    if SAVE:
        os.makedirs("docs/formation_flight", exist_ok=True)
        fig.savefig("docs/formation_flight/design_search.png",
                    dpi=150, bbox_inches="tight")
        print(f"\nSaved to docs/formation_flight/design_search.png")
    else:
        plt.show()


if __name__ == "__main__":
    main()
