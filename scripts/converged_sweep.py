#!/usr/bin/env python3
"""
Full converged analysis across formation configs.

For each config, binary-searches for continuous payload power while preserving
24h energy feasibility. Battery sizing targets dawn_soc = 0.
Uses shared solver from wingz.evaluation.solver.

Usage:
    .venv/bin/python scripts/converged_sweep.py
    .venv/bin/python scripts/converged_sweep.py --save
"""

import sys
import os
import numpy as np
import matplotlib

SAVE = "--save" in sys.argv
if SAVE:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt

from wingz.evaluation.solver import find_max_payload


# ── configs ──────────────────────────────────────────────────────────────────

CONFIGS = [
    ("1x60m", 1, 60),
    ("1x80m", 1, 80),
    ("2x30m", 2, 30),
    ("2x40m", 2, 40),
    ("2x50m", 2, 50),
    ("4x15m", 4, 15),
    ("4x20m", 4, 20),
    ("4x25m", 4, 25),
    ("6x10m", 6, 10),
    ("6x15m", 6, 15),
    ("6x20m", 6, 20),
]


def main():
    print("Running converged sweep (binary-searching 24h-feasible payload)...\n")

    results = []
    for label, N, span in CONFIGS:
        r = find_max_payload(N, span)
        if r is None:
            print(f"  {label}: FAILED TO CONVERGE")
            continue
        r["label"] = label
        r["max_payload_W"] = r["payload_power"]
        results.append(r)
        print(f"  {label}: converged in {r['iterations']} iters, "
              f"AR={r['AR']:.1f}, max_pld={r['max_payload_W']:.0f}W, "
              f"energy_surplus={r['solar_surplus_ratio']*100:.1f}%, cost=${r['cost']/1e6:.2f}M")

    if not results:
        print("No configs converged!")
        return

    # ── summary table ────────────────────────────────────────────────────────
    print("\n" + "=" * 130)
    header = (
        f"{'Config':<10} {'AR':>6} {'Chord':>7} {'Struct/ac':>10} "
        f"{'Bat/ac':>7} {'AC mass':>8} {'Fleet kg':>9} "
        f"{'Pld W':>9} {'Pld kg':>8} {'Cost $M':>8} {'kg/$M':>7} {'Defl%':>7} {'Surplus':>9}"
    )
    print(header)
    print("-" * 130)
    for r in results:
        kg_per_M = r["fleet_mass"] / (r["cost"] / 1e6)
        print(
            f"{r['label']:<10} {r['AR']:>6.1f} {r['chord']:>7.2f} "
            f"{r['struct_each']:>10.2f} "
            f"{r['batt_each']:>7.2f} {r['ac_mass']:>8.2f} "
            f"{r['fleet_mass']:>9.2f} {r['max_payload_W']:>9.0f} "
            f"{r['payload_mass_total']:>8.1f} "
            f"{r['cost']/1e6:>8.3f} {kg_per_M:>7.1f} "
            f"{r['deflection_pct']:>7.1f} {r['solar_surplus_ratio']*100:>8.1f}%"
        )
    print("=" * 130)

    # ── plots ────────────────────────────────────────────────────────────────
    labels = [r["label"] for r in results]
    x = np.arange(len(labels))

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("Converged Formation Sweep — 24h-Feasible Payload", fontsize=14)

    # Panel 1: Per-aircraft mass breakdown (stacked bar)
    ax = axes[0, 0]
    hw_mass = np.array([2.5] * len(results))
    struct_mass = np.array([r["struct_each"] for r in results])
    pld_mass = np.array([r["payload_mass_total"] / r["N"] for r in results])
    batt_mass = np.array([r["batt_each"] for r in results])

    ax.bar(x, struct_mass, label="Structure", color="#2196F3")
    ax.bar(x, hw_mass, bottom=struct_mass, label="Hardware", color="#4CAF50")
    ax.bar(x, pld_mass, bottom=struct_mass + hw_mass, label="Payload", color="#FF9800")
    ax.bar(x, batt_mass, bottom=struct_mass + hw_mass + pld_mass, label="Battery", color="#9C27B0")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("Mass per aircraft (kg)")
    ax.set_title("Per-Aircraft Mass Breakdown")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    # Panel 2: Cost breakdown (stacked bar)
    ax = axes[0, 1]
    cb = [r["cost_breakdown"] for r in results]
    c_struct = np.array([c.structure for c in cb])
    c_solar = np.array([c.solar_cells for c in cb])
    c_batt = np.array([c.batteries for c in cb])
    c_avio = np.array([c.avionics for c in cb])
    c_prop = np.array([c.propulsion for c in cb])
    c_asm = np.array([c.assembly for c in cb])
    c_gnd = np.array([c.ground_infra for c in cb])
    c_tool = np.array([c.capital_amortized for c in cb])

    scale = 1e6
    ax.bar(x, c_struct / scale, label="Structure", color="#2196F3")
    ax.bar(x, c_solar / scale, bottom=c_struct / scale, label="Solar cells", color="#FFC107")
    ax.bar(x, c_batt / scale, bottom=(c_struct + c_solar) / scale, label="Batteries", color="#9C27B0")
    ax.bar(x, c_avio / scale, bottom=(c_struct + c_solar + c_batt) / scale, label="Avionics", color="#4CAF50")
    bottom4 = c_struct + c_solar + c_batt + c_avio
    ax.bar(x, c_prop / scale, bottom=bottom4 / scale, label="Propulsion", color="#FF5722")
    ax.bar(x, (c_asm + c_gnd + c_tool) / scale, bottom=(bottom4 + c_prop) / scale, label="Other", color="#607D8B")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("Cost ($M)")
    ax.set_title("Fleet Cost Breakdown")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")

    # Panel 3: Max continuous payload power vs fleet cost (scatter, labeled)
    ax = axes[1, 0]
    pld_pwr = np.array([r["max_payload_W"] for r in results])
    costs_M = np.array([r["cost"] / 1e6 for r in results])
    ax.scatter(pld_pwr, costs_M, s=80, zorder=5)
    for r in results:
        ax.annotate(
            r["label"],
            xy=(r["max_payload_W"], r["cost"] / 1e6),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=8,
        )
    ax.set_xlabel("Max 24h-feasible continuous payload power (W)")
    ax.set_ylabel("Fleet cost ($M)")
    ax.set_title("Payload Power vs Fleet Cost")
    ax.grid(True, alpha=0.3)

    # Panel 4: kg/$M bar chart
    ax = axes[1, 1]
    kg_per_M = np.array([r["fleet_mass"] / (r["cost"] / 1e6) for r in results])
    bars = ax.bar(x, kg_per_M, color="#009688")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("kg per $M")
    ax.set_title("Fleet Mass per $M (higher = more cost-efficient)")
    ax.grid(True, alpha=0.3, axis="y")
    for bar, val in zip(bars, kg_per_M):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f"{val:.0f}", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()

    if SAVE:
        os.makedirs("docs/formation_flight", exist_ok=True)
        fig.savefig("docs/formation_flight/converged_sweep.png", dpi=150, bbox_inches="tight")
        print("\nFigure saved to docs/formation_flight/converged_sweep.png")
    else:
        plt.show()


if __name__ == "__main__":
    main()
