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
from wingz.structures.beam import BeamStructure
from wingz.solar.power import solar_irradiance, day_length_hours, _solar_declination
from wingz.aerodynamics.formation_aero import (
    per_slot_drag_factor, effective_span, FormationGeometry,
)
from wingz.cost.materials import fleet_cost as fc_fn

beam = BeamStructure()
G = 9.81
RHO = 0.0889
BATT_DENS = 250
V = 25.0
OSWALD = 0.85
CD0 = 0.028  # boom-tail
LAT = 30
DOY = 172

day_h = day_length_hours(LAT, DOY)
night_h = 24 - day_h
sunrise = 12 - day_h / 2
peak_irr = solar_irradiance(20000, LAT, DOY)
avg_irr = (2 / np.pi) * peak_irr


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


def solve_max_payload(N, span, AR, g_per_W=50):
    """Find max payload power where dawn battery >= 0%."""
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
                + q * area_each * CD0
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
            b_eff = effective_span(N, span, 0.1, FormationGeometry.V)
            fc = fc_fn(
                N=N, structural_mass_kg=ns * N, solar_panel_area_m2=total_area,
                battery_capacity_kWh=nb * N * 250 / 1000,
                n_full_nav=1, n_basic_nav=N - 1, production_run=10,
            )
            best = {
                "pp": mid_p, "pm": pm, "cost": fc.total,
                "dpkg": fc.total / max(0.1, pm),
                "ac": ac, "fleet": N * ac,
                "struct": ns, "batt": nb, "pld_each": pld_each,
                "pwr": pwr, "drag": drag, "factors": factors,
                "b_eff": b_eff, "area_each": area_each,
                "avg_factor": sum(factors) / N,
            }
        else:
            hi_p = mid_p
    return best


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
            r = solve_max_payload(N, span, AR)
            if r is None:
                continue
            data["N"].append(N)
            data["dpkg"].append(r["dpkg"] / 1000)  # $k/kg
            data["pm"].append(r["pm"])
            data["cost"].append(r["cost"] / 1e6)
            data["fleet"].append(r["fleet"])
            data["beff"].append(r["b_eff"])
            data["avg_factor"].append(r["avg_factor"])
            data["pp"].append(r["pp"])
            data["ac"].append(r["ac"])
            data["pwr"].append(r["pwr"])
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
