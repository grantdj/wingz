#!/usr/bin/env python3
"""
Full converged analysis across formation configs.

For each config, binary-searches for the payload power that gives 30% energy margin.
Uses a standalone fixed-speed convergence solver (struct + battery iteration).

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

from wingz.structures.beam import BeamStructure
from wingz.solar.power import solar_irradiance, day_length_hours
from wingz.aerodynamics.formation_aero import per_slot_drag_factor, FormationGeometry
from wingz.cost.materials import fleet_cost, FleetCost


# ── solver ──────────────────────────────────────────────────────────────────

def _choose_ar(span):
    """Pick a realistic design AR for a given span (6-14 range per spec)."""
    ar = 5.0 + span / 6.0
    return float(np.clip(ar, 6.0, 14.0))


def solve(N, span, AR=None, pld_power=0, pld_mass_each=0.0):
    """Self-consistent solve: fixed AR geometry, iterate struct+battery+speed.

    Wing area = span² / AR (fixed design geometry).
    Cruise speed from wing loading (self-consistent per sweep engine approach).
    Structure sized from BeamStructure to carry actual loaded weight.
    Battery sized for night energy at converged power draw.

    pld_mass_each: payload mass per aircraft (kg) — caller controls to avoid spiral.
    pld_power: total formation payload power (W).
    """
    rho = 0.0889
    g = 9.81
    CL_MAX = 1.2
    OSWALD_E = 0.85
    CD0 = 0.025
    CRUISE_MARGIN = 1.3
    BATT_ENERGY_DENSITY = 250.0  # Wh/kg

    if AR is None:
        AR = _choose_ar(span)

    hw = 2.5  # hardware mass per aircraft (kg)

    # Wing area fixed by design geometry
    area_each = span ** 2 / AR
    total_area = N * area_each
    chord = span / AR

    factors = per_slot_drag_factor(N, span, 0.1, FormationGeometry.V)

    peak_irr = solar_irradiance(20000, 30, 172)
    day_h = day_length_hours(30, 172)
    night_h = 24 - day_h
    avg_irr = (2 / np.pi) * peak_irr

    sk_total = 5.0 * max(0, N - 1)
    hw_pwr = 15 + 3 * (N - 1)

    struct_each = 5.0
    batt_each = 5.0
    beam = BeamStructure()

    for i in range(300):
        ac = struct_each + hw + pld_mass_each + batt_each
        W = ac * g

        V_stall = np.sqrt(2 * W / (rho * area_each * CL_MAX))
        V_cruise = CRUISE_MARGIN * V_stall
        q = 0.5 * rho * V_cruise ** 2

        drag = sum(
            factors[j] * W ** 2 / (q * np.pi * OSWALD_E * span ** 2)
            + q * area_each * CD0
            for j in range(N)
        )

        total_pwr = drag * V_cruise + hw_pwr + sk_total + pld_power

        new_batt = total_pwr * night_h / BATT_ENERGY_DENSITY / N
        new_struct = beam.wing_mass(span, AR, ac)

        if not np.isfinite(new_batt) or not np.isfinite(new_struct) or new_batt > 1e5:
            return None

        converged = abs(new_batt - batt_each) < 0.05 and abs(new_struct - struct_each) < 0.05
        if converged and i > 0:
            avail = total_area * 0.8 * 0.38 * avg_irr * day_h
            margin = (avail - total_pwr * 24) / (total_pwr * 24)
            defl = beam.deflection_percent(span, AR, ac)

            fc = fleet_cost(
                N=N,
                structural_mass_kg=new_struct * N,
                solar_panel_area_m2=total_area,
                battery_capacity_kWh=new_batt * N * BATT_ENERGY_DENSITY / 1000,
                n_full_nav=1,
                n_basic_nav=N - 1,
                production_run=10,
            )
            return {
                "converged": True,
                "iterations": i + 1,
                "AR": AR,
                "chord": chord,
                "area_each": area_each,
                "struct_each": new_struct,
                "batt_each": new_batt,
                "ac_mass": ac,
                "fleet_mass": N * ac,
                "velocity": V_cruise,
                "wing_loading": W / area_each,
                "total_power": total_pwr,
                "drag": drag,
                "margin": margin,
                "deflection_pct": defl,
                "cost": fc.total,
                "cost_breakdown": fc,
                "payload_mass_total": pld_mass_each * N,
                "payload_power": pld_power,
            }

        batt_each = 0.7 * batt_each + 0.3 * new_batt
        struct_each = 0.7 * struct_each + 0.3 * new_struct

    return None  # didn't converge


def max_daytime_payload_power(N, span, target_margin=0.30):
    """Compute max daytime payload power at 30% energy margin.

    Daytime-only payload: powered only during the day (no night battery draw).
    This avoids the mass spiral from payload-driven battery growth.
    The 30% margin is on the day-night autonomous system power.

    Returns (base_result, max_daytime_payload_W).
    """
    base = solve(N, span)
    if base is None:
        return None, None

    AR = base["AR"]
    total_area = N * base["area_each"]

    peak_irr = solar_irradiance(20000, 30, 172)
    day_h = day_length_hours(30, 172)
    avg_irr = (2 / np.pi) * peak_irr

    # Available daytime solar energy
    avail_Wh = total_area * 0.8 * 0.38 * avg_irr * day_h

    # Required energy for base system at 30% margin
    # E_avail / (1 + margin) = E_required
    # 30% margin means: E_avail = E_required * 1.30
    # So E_required = E_avail / 1.30
    e_required_Wh = avail_Wh / (1 + target_margin)

    # Base system uses: total_power * 24h
    base_energy_Wh = base["total_power"] * 24

    # Surplus available for daytime payload (only collected during day)
    surplus_Wh = e_required_Wh - base_energy_Wh

    if surplus_Wh <= 0:
        # Base system already exceeds 30% margin budget
        max_pld_pwr = 0.0
    else:
        # Payload power * day_h = surplus_Wh (payload only runs during day)
        max_pld_pwr = surplus_Wh / day_h

    # Return result with max payload power noted
    result = dict(base)
    result["max_daytime_payload_W"] = max(0.0, max_pld_pwr)
    result["solar_available_Wh"] = avail_Wh
    result["base_energy_Wh"] = base_energy_Wh
    return result


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
    print("Running converged sweep (binary-searching for 30% energy margin)...\n")

    results = []
    for label, N, span in CONFIGS:
        r = max_daytime_payload_power(N, span)
        if r is None:
            print(f"  {label}: FAILED TO CONVERGE")
            continue
        r["label"] = label
        r["N"] = N
        r["span"] = span
        results.append(r)
        print(f"  {label}: converged in {r['iterations']} iters, "
              f"AR={r['AR']:.1f}, max_pld={r['max_daytime_payload_W']:.0f}W, "
              f"base_margin={r['margin']*100:.0f}%, cost=${r['cost']/1e6:.2f}M")

    if not results:
        print("No configs converged!")
        return

    # ── summary table ────────────────────────────────────────────────────────
    print("\n" + "=" * 130)
    header = (
        f"{'Config':<10} {'AR':>6} {'Chord':>7} {'Struct/ac':>10} "
        f"{'Bat/ac':>7} {'AC mass':>8} {'Fleet kg':>9} "
        f"{'MaxPld W':>9} {'Cost $M':>8} {'kg/$M':>7} {'Defl%':>7} {'BaseMargin':>11}"
    )
    print(header)
    print("-" * 130)
    for r in results:
        kg_per_M = r["fleet_mass"] / (r["cost"] / 1e6)
        print(
            f"{r['label']:<10} {r['AR']:>6.1f} {r['chord']:>7.2f} "
            f"{r['struct_each']:>10.2f} "
            f"{r['batt_each']:>7.2f} {r['ac_mass']:>8.2f} "
            f"{r['fleet_mass']:>9.2f} {r['max_daytime_payload_W']:>9.0f} "
            f"{r['cost']/1e6:>8.3f} {kg_per_M:>7.1f} "
            f"{r['deflection_pct']:>7.1f} {r['margin']*100:>10.0f}%"
        )
    print("=" * 130)

    # ── plots ────────────────────────────────────────────────────────────────
    labels = [r["label"] for r in results]
    x = np.arange(len(labels))

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("Converged Formation Sweep — 30% Energy Margin", fontsize=14)

    # Panel 1: Per-aircraft mass breakdown (stacked bar)
    ax = axes[0, 0]
    hw_mass = np.array([2.5] * len(results))
    struct_mass = np.array([r["struct_each"] for r in results])
    pld_mass = np.array([0.0] * len(results))  # zero-mass baseline config
    batt_mass = np.array([r["batt_each"] for r in results])

    ax.bar(x, struct_mass, label="Structure", color="#2196F3")
    ax.bar(x, hw_mass, bottom=struct_mass, label="Hardware", color="#4CAF50")
    ax.bar(x, batt_mass, bottom=struct_mass + hw_mass, label="Battery", color="#9C27B0")
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
    c_tool = np.array([c.tooling_amortized for c in cb])

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

    # Panel 3: Max daytime payload power vs fleet cost (scatter, labeled)
    ax = axes[1, 0]
    pld_pwr = np.array([r["max_daytime_payload_W"] for r in results])
    costs_M = np.array([r["cost"] / 1e6 for r in results])
    ax.scatter(pld_pwr, costs_M, s=80, zorder=5)
    for r in results:
        ax.annotate(
            r["label"],
            xy=(r["max_daytime_payload_W"], r["cost"] / 1e6),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=8,
        )
    ax.set_xlabel("Max daytime payload power at 30% margin (W)")
    ax.set_ylabel("Fleet cost ($M)")
    ax.set_title("Max Payload Power (30% margin) vs Fleet Cost")
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
