#!/usr/bin/env python3
"""
Simulate launch-to-altitude for a formation configuration.

Starts at sea level at sunrise with full battery. Simulates in 6-minute
steps for up to 48 hours. Plots altitude, battery %, and power vs time.

Usage:
    .venv/bin/python scripts/climb_profile.py [--save] [--N 2] [--span 40]
"""

import sys
import os
import argparse
import numpy as np
import matplotlib

SAVE = "--save" in sys.argv
if SAVE:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from wingz.evaluation.solver import simulate_climb
from wingz.constants import CRUISE_ALTITUDE_M


def _parse_args():
    p = argparse.ArgumentParser(description="Climb profile simulation")
    p.add_argument("--N", type=int, default=2, help="Number of aircraft")
    p.add_argument("--span", type=float, default=40.0, help="Span per aircraft (m)")
    p.add_argument("--save", action="store_true")
    return p.parse_args()


def _night_spans(time_h, day_h, sunrise_h):
    """Return list of (t_start, t_end) night intervals for shading."""
    spans = []
    t_min, t_max = time_h[0], time_h[-1]

    # first night if simulation starts before sunrise
    if t_min < sunrise_h:
        spans.append((t_min, sunrise_h))

    # full day/night cycles
    day_start = sunrise_h
    while day_start < t_max:
        night_start = day_start + day_h
        night_end = night_start + (24 - day_h)
        if night_start < t_max:
            spans.append((night_start, min(night_end, t_max)))
        day_start += 24

    return spans


def main():
    args = _parse_args()
    N, span = args.N, args.span

    print(f"Simulating {N}x{span:.0f}m formation climb profile...")
    data = simulate_climb(N, span)

    print(f"  Aircraft mass: {data['ac_mass']:.2f} kg/ac")
    print(f"  Battery capacity: {data['batt_cap_Wh']:.1f} Wh/ac")
    max_alt = data["alt_m"].max()
    print(f"  Max altitude reached: {max_alt/1000:.1f} km")
    print(f"  Cruise altitude reached: {data['reached_target']}")

    t = data["time_h"]
    night_spans = _night_spans(t, data["day_h"], data["sunrise_h"])

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.suptitle(f"Launch-to-Altitude: {N}x{span:.0f}m Formation", fontsize=14)

    def shade_night(ax):
        for ts, te in night_spans:
            ax.axvspan(ts, te, alpha=0.15, color="navy", label="_nolegend_")

    # Panel 1: Altitude
    ax = axes[0]
    ax.plot(t, data["alt_m"] / 1000, color="#2196F3", lw=2)
    ax.axhline(CRUISE_ALTITUDE_M / 1000, color="red", ls="--", lw=1, label="Target (20km)")
    shade_night(ax)
    ax.set_ylabel("Altitude (km)")
    ax.set_title("Altitude vs Time")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)

    # Panel 2: Battery %
    ax = axes[1]
    ax.plot(t, data["batt_pct"], color="#9C27B0", lw=2)
    ax.axhline(100, color="gray", ls=":", lw=1)
    ax.axhline(0, color="red", ls="--", lw=1)
    shade_night(ax)
    ax.set_ylabel("Battery (%)")
    ax.set_title("Battery State of Charge")
    ax.set_ylim(-5, 110)
    ax.grid(True, alpha=0.3)

    # Panel 3: Power
    ax = axes[2]
    ax.plot(t, data["solar_W"] / 1000, color="#FF9800", lw=2, label="Solar power")
    ax.plot(t, data["lvl_pwr_W"] / 1000, color="#F44336", lw=2, label="Level flight power")
    shade_night(ax)
    ax.set_xlabel("Time (h from launch day sunrise)")
    ax.set_ylabel("Power (kW) — formation total")
    ax.set_title("Solar vs Required Power")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)

    night_patch = mpatches.Patch(color="navy", alpha=0.15, label="Night")
    axes[0].legend(handles=[axes[0].get_lines()[0], axes[0].get_lines()[1], night_patch],
                   labels=["Altitude", "Target (20km)", "Night"], loc="lower right")

    plt.tight_layout()

    if SAVE:
        os.makedirs("docs/formation_flight", exist_ok=True)
        fig.savefig("docs/formation_flight/climb_profile_sim.png", dpi=150, bbox_inches="tight")
        print("\nFigure saved to docs/formation_flight/climb_profile_sim.png")
    else:
        plt.show()


if __name__ == "__main__":
    main()
