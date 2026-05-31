#!/usr/bin/env python3
"""
Formation scaling: how does $/kg payload change as fleet size grows?

Runs the full converged solver (beam structure, battery, 24h sim) at
each fleet size N from 1 to 12, keeping total mission capability
comparable by fixing span per aircraft.

Usage:
    .venv/bin/python scripts/formation_scaling.py
    .venv/bin/python scripts/formation_scaling.py --save
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
from wingz.aerodynamics.formation_aero import effective_span, FormationGeometry


def main():
    # Sweep N for several span choices
    span_configs = [
        (15, 10, "15m span, AR=10"),
        (20, 10, "20m span, AR=10"),
        (30, 10, "30m span, AR=10"),
        (40, 12, "40m span, AR=12"),
    ]

    Ns = list(range(1, 13))

    print("Sweeping fleet size N=1..12 for each span...\n")

    all_data = {}
    for span, AR, label in span_configs:
        print(f"  {label}:", end="", flush=True)
        data = {"N": [], "dpkg": [], "pm": [], "cost": [],
                "fleet": [], "beff": [], "avg_factor": [],
                "pp": [], "ac": [], "pwr": []}
        for N in Ns:
            r = find_max_payload(N, span, AR=AR)
            if r is None:
                continue
            pm = r["payload_mass_total"]
            cost = r["cost"]
            dpkg = cost / max(0.1, pm)
            b_eff = effective_span(N, span, 0.1, FormationGeometry.V)
            from wingz.aerodynamics.formation_aero import per_slot_drag_factor
            factors = per_slot_drag_factor(N, span, 0.1, FormationGeometry.V)
            avg_factor = sum(factors) / N
            data["N"].append(N)
            data["dpkg"].append(dpkg / 1000)  # $k/kg
            data["pm"].append(pm)
            data["cost"].append(cost / 1e6)
            data["fleet"].append(r["fleet_mass"])
            data["beff"].append(b_eff)
            data["avg_factor"].append(avg_factor)
            data["pp"].append(r["payload_power"])
            data["ac"].append(r["ac_mass"])
            data["pwr"].append(r["P_day"])
            print(f" N={N}", end="", flush=True)
        print()
        all_data[label] = data

    # Print table
    print()
    for label, data in all_data.items():
        print(f"--- {label} ---")
        print(f"{'N':>3} {'$/kg(k)':>8} {'Payload':>8} {'Fleet':>7} "
              f"{'Cost($M)':>8} {'b_eff':>6} {'AvgFact':>8} {'AC(kg)':>7} {'PldPwr':>7}")
        print("-" * 75)
        for i in range(len(data["N"])):
            print(f"{data['N'][i]:>3} {data['dpkg'][i]:>8.1f} "
                  f"{data['pm'][i]:>8.1f} {data['fleet'][i]:>7.1f} "
                  f"{data['cost'][i]:>8.2f} {data['beff'][i]:>6.1f} "
                  f"{data['avg_factor'][i]:>8.3f} {data['ac'][i]:>7.1f} "
                  f"{data['pp'][i]:>7.0f}")
        print()

    # Plot
    fig, axes = plt.subplots(2, 3, figsize=(18, 11))

    colors = ["tab:blue", "tab:orange", "tab:green", "tab:red"]

    # 1: $/kg vs N
    ax = axes[0, 0]
    for (label, data), color in zip(all_data.items(), colors):
        ax.plot(data["N"], data["dpkg"], "o-", color=color, lw=2, label=label)
    ax.set_xlabel("Fleet size (N)")
    ax.set_ylabel("$/kg payload (thousands)")
    ax.set_title("Cost per kg Payload vs Fleet Size")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 2: Total payload mass vs N
    ax = axes[0, 1]
    for (label, data), color in zip(all_data.items(), colors):
        ax.plot(data["N"], data["pm"], "o-", color=color, lw=2, label=label)
    ax.set_xlabel("Fleet size (N)")
    ax.set_ylabel("Total payload mass (kg)")
    ax.set_title("Payload Capacity vs Fleet Size")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 3: Fleet cost vs N
    ax = axes[0, 2]
    for (label, data), color in zip(all_data.items(), colors):
        ax.plot(data["N"], data["cost"], "o-", color=color, lw=2, label=label)
    ax.set_xlabel("Fleet size (N)")
    ax.set_ylabel("Fleet cost ($M)")
    ax.set_title("Total Fleet Cost vs Fleet Size")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 4: Average drag factor vs N
    ax = axes[1, 0]
    for (label, data), color in zip(all_data.items(), colors):
        ax.plot(data["N"], data["avg_factor"], "o-", color=color, lw=2, label=label)
    ax.set_xlabel("Fleet size (N)")
    ax.set_ylabel("Fleet-average drag factor")
    ax.set_title("Average Drag Factor vs Fleet Size\n(lower = more wake benefit)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.1)

    # 5: Effective span vs N
    ax = axes[1, 1]
    for (label, data), color in zip(all_data.items(), colors):
        ax.plot(data["N"], data["beff"], "o-", color=color, lw=2, label=label)
        # Also plot N*span as theoretical max
        span_val = int(label.split("m")[0])
        ax.plot(data["N"], [n * span_val for n in data["N"]],
                "--", color=color, alpha=0.3)
    ax.set_xlabel("Fleet size (N)")
    ax.set_ylabel("Effective span (m)")
    ax.set_title("Effective Span vs Fleet Size\n(dashed = N*span theoretical max)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 6: Per-aircraft mass vs N
    ax = axes[1, 2]
    for (label, data), color in zip(all_data.items(), colors):
        ax.plot(data["N"], data["ac"], "o-", color=color, lw=2, label=label)
    ax.set_xlabel("Fleet size (N)")
    ax.set_ylabel("Per-aircraft mass (kg)")
    ax.set_title("Vehicle Mass vs Fleet Size")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.suptitle(
        "Formation Scaling: Cost, Payload, and Drag vs Fleet Size\n"
        "Boom-tail, V formation, 10% overlap, 0% dawn battery, beam structure",
        fontsize=14, y=1.02,
    )
    plt.tight_layout()

    if SAVE:
        os.makedirs("docs/formation_flight", exist_ok=True)
        fig.savefig("docs/formation_flight/formation_scaling.png",
                    dpi=150, bbox_inches="tight")
        print("\nSaved to docs/formation_flight/formation_scaling.png")
    else:
        plt.show()


if __name__ == "__main__":
    main()
