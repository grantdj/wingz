#!/usr/bin/env python3
"""
Span vs chord heatmaps showing $/kg payload and payload mass.

Sweeps span and chord for N=1, N=2, N=4 formations with boom-tail
configuration. Uses beam structural model, 0% dawn battery, 24h
simulation for energy balance.

Usage:
    .venv/bin/python scripts/span_chord_sweep.py
    .venv/bin/python scripts/span_chord_sweep.py --save
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

# Airframe configs: min_chord, label (cd0 not used by shared solver — uses CD0 from constants)
AIRFRAME_TYPES = {
    "boom_tail": {"min_chord": 0.5, "label": "Boom-Tail"},
    "flying_wing": {"min_chord": 1.5, "label": "Flying Wing"},
    "conventional": {"min_chord": 1.0, "label": "Conventional"},
}


def main():
    airframe = AIRFRAME_TYPES["boom_tail"]
    min_chord = airframe["min_chord"]
    label = airframe["label"]

    spans = np.arange(8, 65, 2)
    chords = np.arange(0.5, 6.1, 0.25)
    fleet_configs = [("Single (N=1)", 1), ("Formation 2x", 2), ("Formation 4x", 4)]

    print(f"Sweeping span x chord for {label} (min chord={min_chord}m)...")

    fig, axes = plt.subplots(2, 3, figsize=(18, 11))

    for idx, (name, N) in enumerate(fleet_configs):
        print(f"  {name}...", end="", flush=True)
        dpkg_grid = np.full((len(chords), len(spans)), np.nan)
        pm_grid = np.full((len(chords), len(spans)), np.nan)

        for i, span in enumerate(spans):
            for j, chord in enumerate(chords):
                if chord < min_chord:
                    continue
                AR = span / chord
                if AR < 3 or AR > 50:
                    continue
                r = find_max_payload(N, span, AR=AR)
                if r is not None and r["payload_mass_total"] > 0.5:
                    pm = r["payload_mass_total"]
                    dpkg_grid[j, i] = r["cost"] / max(0.1, pm) / 1000
                    pm_grid[j, i] = pm

        print(" done")

        # $/kg heatmap
        ax = axes[0, idx]
        im = ax.pcolormesh(spans, chords, dpkg_grid, shading="auto",
                           cmap="viridis_r", vmin=8, vmax=80)
        plt.colorbar(im, ax=ax, label=r"$/kg payload (thousands)")
        ax.set_xlabel("Span (m)")
        ax.set_ylabel("Chord (m)")
        ax.set_title(f"{name} — $/kg payload")
        ax.set_ylim(0.5, 6)

        # Payload mass heatmap
        ax = axes[1, idx]
        im = ax.pcolormesh(spans, chords, pm_grid, shading="auto",
                           cmap="YlOrRd", vmin=0, vmax=400)
        plt.colorbar(im, ax=ax, label="Payload mass (kg)")
        ax.set_xlabel("Span (m)")
        ax.set_ylabel("Chord (m)")
        ax.set_title(f"{name} — Payload mass (kg)")
        ax.set_ylim(0.5, 6)

    from wingz.constants import CD0
    plt.suptitle(
        f"Span vs Chord: Cost per kg Payload and Payload Mass\n"
        f"{label} config, Cd0={CD0}, beam structure",
        fontsize=13, y=1.02,
    )
    plt.tight_layout()

    if SAVE:
        os.makedirs("docs/formation_flight", exist_ok=True)
        fig.savefig("docs/formation_flight/span_chord_cost.png",
                    dpi=150, bbox_inches="tight")
        print("\nSaved to docs/formation_flight/span_chord_cost.png")
    else:
        plt.show()


if __name__ == "__main__":
    main()
