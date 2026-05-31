#!/usr/bin/env python3
"""
24-hour energy profile at cruise altitude.

Shows solar collection, battery charge/discharge, and wasted power for
multiple configs side by side. Simulates one 24h cycle starting at dawn
with empty battery (worst case after night).

Usage:
    .venv/bin/python scripts/energy_timeline.py
    .venv/bin/python scripts/energy_timeline.py --save
"""

import sys
import os
import numpy as np
import matplotlib

SAVE = "--save" in sys.argv
if SAVE:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt

from wingz.evaluation.solver import find_max_payload, simulate_24h
from wingz.constants import BATTERY_ENERGY_DENSITY

# Configs: (N, span) — AR is computed by the solver, not hardcoded
CONFIGS = [
    (1, 60),
    (2, 40),
    (4, 20),
    (6, 10),
]

COLORS = ["#2196F3", "#4CAF50", "#FF9800", "#E91E63"]


def main():
    print("Simulating 24h energy profiles at cruise altitude...")
    print("Finding max 24h-feasible continuous payload, then simulating 24h cycle.\n")

    datasets = []
    for N, span in CONFIGS:
        r = find_max_payload(N, span)
        if r is None:
            print(f"  {N}x{span}m: FAILED TO CONVERGE")
            continue
        label = f"{N}x{span}m AR={r['AR']:.1f}"
        batt_cap_Wh = r["batt_each"] * BATTERY_ENERGY_DENSITY
        sim = simulate_24h(
            total_area=N * r["area_each"],
            batt_cap_Wh=batt_cap_Wh,
            power_required=r["P_night"],
        )
        sim["label"] = label
        sim["N"] = N
        sim["span"] = span
        datasets.append(sim)
        print(f"  {label}: pld={r['payload_power']:.0f}W, req={r['P_night']:.0f}W, "
              f"batt_cap={batt_cap_Wh:.0f}Wh/ac, ac={r['ac_mass']:.0f}kg")

    if not datasets:
        print("No configs converged!")
        return

    fig, axes = plt.subplots(3, 1, figsize=(14, 11), sharex=True)
    fig.suptitle("24-Hour Energy Profile at Cruise Altitude (20km, dawn start, empty battery)",
                 fontsize=13)

    # Panel 1: Solar vs required power
    ax = axes[0]
    for i, d in enumerate(datasets):
        t = d["time_h"]
        ax.plot(t, d["solar_W"] / 1000, color=COLORS[i % len(COLORS)], lw=2,
                label=d["label"])
        ax.plot(t, d["req_W"] / 1000, color=COLORS[i % len(COLORS)], lw=1.5,
                ls="--", alpha=0.7)
    # Night shading
    day_h = datasets[0]["day_h"]
    sunset = day_h
    ax.axvspan(sunset, 24, alpha=0.15, color="navy")
    ax.axvspan(0, 0, alpha=0.15, color="navy", label="Night")
    ax.set_ylabel("Power (kW) — formation total")
    ax.set_title("Solar Power (solid) vs Required Power (dashed)")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)

    # Panel 2: Battery state of charge
    ax = axes[1]
    for i, d in enumerate(datasets):
        t = d["time_h"]
        ax.plot(t, d["batt_pct"], color=COLORS[i % len(COLORS)], lw=2,
                label=d["label"])
    ax.axvspan(sunset, 24, alpha=0.15, color="navy")
    ax.axhline(100, color="gray", ls=":", lw=1, label="Full")
    ax.axhline(0, color="red", ls="--", lw=1, label="Empty")
    ax.set_ylabel("Battery SoC (% per aircraft)")
    ax.set_title("Battery State of Charge")
    ax.legend(fontsize=8, ncol=2)
    ax.set_ylim(-5, 115)
    ax.grid(True, alpha=0.3)

    # Panel 3: Wasted power (clipped solar)
    ax = axes[2]
    for i, d in enumerate(datasets):
        t = d["time_h"]
        ax.plot(t, d["waste_W"] / 1000, color=COLORS[i % len(COLORS)], lw=2,
                label=d["label"])
    ax.axvspan(sunset, 24, alpha=0.15, color="navy")
    ax.set_xlabel("Hours from dawn")
    ax.set_ylabel("Wasted power (kW) — formation total")
    ax.set_title("Clipped / Wasted Solar Power (battery full)")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)

    plt.tight_layout()

    if SAVE:
        os.makedirs("docs/formation_flight", exist_ok=True)
        fig.savefig("docs/formation_flight/energy_timeline.png", dpi=150, bbox_inches="tight")
        print("\nFigure saved to docs/formation_flight/energy_timeline.png")
    else:
        plt.show()


if __name__ == "__main__":
    main()
