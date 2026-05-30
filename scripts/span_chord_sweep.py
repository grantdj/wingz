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

from wingz.structures.beam import BeamStructure
from wingz.solar.power import solar_irradiance, day_length_hours, _solar_declination
from wingz.aerodynamics.formation_aero import per_slot_drag_factor, FormationGeometry
from wingz.cost.materials import fleet_cost as fc_fn

beam = BeamStructure()
G = 9.81
RHO = 0.0889
BATT_DENS = 250
V = 25.0
OSWALD = 0.85
LAT = 30
DOY = 172

day_h = day_length_hours(LAT, DOY)
night_h = 24 - day_h
sunrise = 12 - day_h / 2

# Airframe configs: cd0, min_chord, label
AIRFRAME_TYPES = {
    "boom_tail": {"cd0": 0.028, "min_chord": 0.5, "label": "Boom-Tail"},
    "flying_wing": {"cd0": 0.020, "min_chord": 1.5, "label": "Flying Wing"},
    "conventional": {"cd0": 0.035, "min_chord": 1.0, "label": "Conventional"},
}


def solar_at_hour(total_area, hod):
    ha = np.radians((hod - 12) * 15)
    dec = _solar_declination(DOY)
    sin_el = (np.sin(np.radians(LAT)) * np.sin(dec)
              + np.cos(np.radians(LAT)) * np.cos(dec) * np.cos(ha))
    if sin_el <= 0:
        return 0
    tau = 0.3 * np.exp(-20000 / 8500)
    return total_area * 0.8 * 0.38 * 1361 * np.exp(-tau / max(sin_el, 0.01))


def sim_dawn(total_area, pwr, batt_cap):
    dt = 0.05
    batt = 0
    for s in range(int(24 / dt)):
        hod = (sunrise + s * dt) % 24
        net = solar_at_hour(total_area, hod) - pwr
        if net > 0:
            batt = min(batt + net * dt, batt_cap)
        else:
            batt += net * dt
    return batt / batt_cap if batt_cap > 0 else -1


def solve(N, span, AR, cd0, g_per_W=50):
    area_each = span**2 / AR
    total_area = N * area_each
    factors = per_slot_drag_factor(N, span, 0.1, FormationGeometry.V)
    q = 0.5 * RHO * V**2
    hw = 2.5
    sk = 5.0 * max(0, N - 1)
    hp = 15 + 3 * (N - 1)

    lo_p, hi_p = 0, 15000
    best = None
    for _ in range(30):
        mid_p = (lo_p + hi_p) / 2
        pld_each = mid_p * g_per_W / 1000 / N
        s = 5.0
        b = 5.0
        converged = False
        for _ in range(200):
            ac = s + hw + pld_each + b
            W = ac * G
            drag = sum(
                factors[j] * W**2 / (q * np.pi * OSWALD * span**2)
                + q * area_each * cd0
                for j in range(N)
            )
            pwr = drag * V + hp + sk + mid_p
            nb = pwr * night_h / BATT_DENS / N
            ns = beam.wing_mass(span, AR, ac)
            if not np.isfinite(nb) or nb > 1e5:
                break
            if abs(nb - b) < 0.05 and abs(ns - s) < 0.05:
                converged = True
                break
            b = 0.7 * b + 0.3 * nb
            s = 0.7 * s + 0.3 * ns
        if not converged:
            hi_p = mid_p
            continue
        bc = b * BATT_DENS * N
        dawn = sim_dawn(total_area, pwr, bc)
        if dawn >= -0.02:
            lo_p = mid_p
            pm = pld_each * N
            fc = fc_fn(
                N=N, structural_mass_kg=ns * N, solar_panel_area_m2=total_area,
                battery_capacity_kWh=nb * N * 250 / 1000,
                n_full_nav=1, n_basic_nav=N - 1, production_run=10,
            )
            best = {
                "pp": mid_p, "pm": pm, "cost": fc.total,
                "dpkg": fc.total / max(0.1, pm),
                "ac": ac, "fleet": N * ac, "chord": span / AR, "AR": AR,
                "struct": ns, "batt": nb, "pld_each": pld_each, "area": area_each,
            }
        else:
            hi_p = mid_p
    return best


def main():
    airframe = AIRFRAME_TYPES["boom_tail"]
    cd0 = airframe["cd0"]
    min_chord = airframe["min_chord"]
    label = airframe["label"]

    spans = np.arange(8, 65, 2)
    chords = np.arange(0.5, 6.1, 0.25)
    fleet_configs = [("Single (N=1)", 1), ("Formation 2x", 2), ("Formation 4x", 4)]

    print(f"Sweeping span x chord for {label} (Cd0={cd0}, min chord={min_chord}m)...")

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
                r = solve(N, span, AR, cd0)
                if r is not None and r["pm"] > 0.5:
                    dpkg_grid[j, i] = r["dpkg"] / 1000
                    pm_grid[j, i] = r["pm"]

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

    plt.suptitle(
        f"Span vs Chord: Cost per kg Payload and Payload Mass\n"
        f"{label} config, Cd0={cd0}, V={V} m/s, 0% dawn battery, beam structure",
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
