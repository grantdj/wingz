#!/usr/bin/env python3
"""
Cost vs payload analysis with realistic pricing.

For each config, sweeps continuous payload power from 0 to the maximum that
preserves 24h energy feasibility,
computing cost using fleet_cost() from wingz.cost.materials.

Usage:
    .venv/bin/python scripts/cost_comparison.py
    .venv/bin/python scripts/cost_comparison.py --save
"""

import sys
import os
import numpy as np
import matplotlib

SAVE = "--save" in sys.argv
if SAVE:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt

from wingz.evaluation.solver import solve_converged, find_max_payload

CONFIGS = [
    ("1x60m", 1, 60),
    ("2x40m", 2, 40),
    ("4x20m", 4, 20),
    ("6x15m", 6, 15),
]

COLORS = ["#2196F3", "#4CAF50", "#FF9800", "#E91E63"]


def payload_power_sweep(N, span, n_points=25):
    """Sweep continuous payload power across the 24h-feasible range."""
    best = find_max_payload(N, span)
    if best is None:
        return []
    max_pld_pwr = best["payload_power"]

    rows = []
    for pld_pwr in np.linspace(0, max_pld_pwr, n_points):
        result = solve_converged(N, span, pld_power=pld_pwr)
        if result is not None:
            rows.append(result)

    return rows


def main():
    print("Running cost vs payload sweep...\n")

    config_data = {}
    max_payloads = {}

    for label, N, span in CONFIGS:
        print(f"  {label}: sweeping continuous payload power...")
        rows = payload_power_sweep(N, span, n_points=25)
        if not rows:
            print(f"    -> no valid range found")
            continue
        config_data[label] = rows
        max_payloads[label] = rows[-1]["payload_power"]
        print(f"    -> max 24h-feasible continuous payload = {max_payloads[label]:.0f} W, "
              f"cost = ${rows[-1]['cost']/1e6:.2f}M")

    if not config_data:
        print("No configs converged!")
        return

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("Cost vs Payload — Realistic Pricing (fleet_cost)", fontsize=14)

    # Panel 1: System cost vs payload power
    ax = axes[0, 0]
    for i, (label, rows) in enumerate(config_data.items()):
        pwr = [r["payload_power"] for r in rows]
        cost = [r["cost"] / 1e6 for r in rows]
        ax.plot(pwr, cost, color=COLORS[i % len(COLORS)], lw=2, marker="o",
                markersize=3, label=label)
    ax.set_xlabel("Payload power (W)")
    ax.set_ylabel("Fleet cost ($M)")
    ax.set_title("System Cost vs Payload Power")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Panel 2: $/W of payload vs payload power
    ax = axes[0, 1]
    for i, (label, rows) in enumerate(config_data.items()):
        pwr = np.array([r["payload_power"] for r in rows])
        cost = np.array([r["cost"] for r in rows])
        # Avoid division by zero at p=0
        valid = pwr > 10
        if valid.any():
            ax.plot(pwr[valid], cost[valid] / pwr[valid],
                    color=COLORS[i % len(COLORS)], lw=2, marker="o", markersize=3,
                    label=label)
    ax.set_xlabel("Payload power (W)")
    ax.set_ylabel("Cost per watt of payload ($/W)")
    ax.set_title("$/W of Payload vs Payload Power")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)

    # Panel 3: kg/$M vs payload power
    ax = axes[1, 0]
    for i, (label, rows) in enumerate(config_data.items()):
        pwr = [r["payload_power"] for r in rows]
        kg_M = [r["fleet_mass"] / (r["cost"] / 1e6) for r in rows]
        ax.plot(pwr, kg_M, color=COLORS[i % len(COLORS)], lw=2, marker="o",
                markersize=3, label=label)
    ax.set_xlabel("Payload power (W)")
    ax.set_ylabel("kg per $M")
    ax.set_title("Fleet Mass per $M vs Payload Power")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Panel 4: Cost breakdown at max feasible payload (stacked bar)
    ax = axes[1, 1]
    labels_at_max = []
    cb_list = []

    for label, rows in config_data.items():
        # Use the last row at max payload power.
        best = rows[-1]
        labels_at_max.append(label)
        cb_list.append(best["cost_breakdown"])

    x = np.arange(len(labels_at_max))
    scale = 1e6

    c_struct = np.array([c.structure for c in cb_list]) / scale
    c_solar  = np.array([c.solar_cells for c in cb_list]) / scale
    c_batt   = np.array([c.batteries for c in cb_list]) / scale
    c_avio   = np.array([c.avionics for c in cb_list]) / scale
    c_prop   = np.array([c.propulsion for c in cb_list]) / scale
    c_other  = np.array([c.assembly + c.ground_infra + c.capital_amortized
                          for c in cb_list]) / scale

    ax.bar(x, c_struct, label="Structure", color="#2196F3")
    ax.bar(x, c_solar,  bottom=c_struct, label="Solar", color="#FFC107")
    ax.bar(x, c_batt,   bottom=c_struct + c_solar, label="Battery", color="#9C27B0")
    ax.bar(x, c_avio,   bottom=c_struct + c_solar + c_batt, label="Avionics", color="#4CAF50")
    b4 = c_struct + c_solar + c_batt + c_avio
    ax.bar(x, c_prop,   bottom=b4, label="Propulsion", color="#FF5722")
    ax.bar(x, c_other,  bottom=b4 + c_prop, label="Other", color="#607D8B")

    ax.set_xticks(x)
    ax.set_xticklabels(labels_at_max, rotation=20, ha="right")
    ax.set_ylabel("Cost ($M)")
    ax.set_title("Cost Breakdown at Max Feasible Payload")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()

    if SAVE:
        os.makedirs("docs/formation_flight", exist_ok=True)
        fig.savefig("docs/formation_flight/cost_comparison.png", dpi=150, bbox_inches="tight")
        print("\nFigure saved to docs/formation_flight/cost_comparison.png")
    else:
        plt.show()


if __name__ == "__main__":
    main()
