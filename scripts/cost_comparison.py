#!/usr/bin/env python3
"""
Cost vs payload analysis with realistic pricing.

For each config, sweeps payload power from 0 to max (where margin hits 30%),
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

from wingz.structures.beam import BeamStructure
from wingz.solar.power import solar_irradiance, day_length_hours
from wingz.aerodynamics.formation_aero import per_slot_drag_factor, FormationGeometry
from wingz.cost.materials import fleet_cost, FleetCost

# ── constants ──────────────────────────────────────────────────────────────

G = 9.81
CL_MAX = 1.2
BATT_ENERGY_DENSITY = 250.0
PANEL_EFF = 0.38
PANEL_COVERAGE = 0.80
CD0 = 0.025
OSWALD_E = 0.85
RHO = 0.0889
V_CRUISE = 25.0
LAT_DEG = 30.0
DOY = 172
TARGET_MARGIN = 0.30
PLD_G_PER_W = 50  # g/W payload specific mass

CONFIGS = [
    ("1x60m", 1, 60),
    ("2x40m", 2, 40),
    ("4x20m", 4, 20),
    ("6x15m", 6, 15),
]

COLORS = ["#2196F3", "#4CAF50", "#FF9800", "#E91E63"]


# ── solver (fixed-AR geometry) ───────────────────────────────────────────────

def _choose_ar(span):
    """Pick a realistic design AR for a given span (6-14 range per spec)."""
    ar = 5.0 + span / 6.0
    return float(np.clip(ar, 6.0, 14.0))


def _solve_base(N, span):
    """Converge base aircraft (no payload). Returns result dict."""
    rho = RHO
    g = G
    hw = 2.5

    AR = _choose_ar(span)
    area_each = span ** 2 / AR
    total_area = N * area_each
    chord = span / AR

    factors = per_slot_drag_factor(N, span, 0.1, FormationGeometry.V)
    peak_irr = solar_irradiance(20000, LAT_DEG, DOY)
    day_h = day_length_hours(LAT_DEG, DOY)
    night_h = 24 - day_h
    avg_irr = (2 / np.pi) * peak_irr
    sk_total = 5.0 * max(0, N - 1)
    hw_pwr = 15 + 3 * (N - 1)

    struct_each = 5.0
    batt_each = 5.0
    beam = BeamStructure()

    for _ in range(300):
        ac = struct_each + hw + batt_each
        W = ac * g
        V_cruise = 1.3 * np.sqrt(2 * W / (rho * area_each * CL_MAX))
        q = 0.5 * rho * V_cruise ** 2

        drag = sum(
            factors[j] * W ** 2 / (q * np.pi * OSWALD_E * span ** 2)
            + q * area_each * CD0
            for j in range(N)
        )
        total_pwr = drag * V_cruise + hw_pwr + sk_total
        new_batt = total_pwr * night_h / BATT_ENERGY_DENSITY / N
        new_struct = beam.wing_mass(span, AR, ac)

        if not np.isfinite(new_batt) or not np.isfinite(new_struct) or new_batt > 1e5:
            return None

        if abs(new_batt - batt_each) < 0.05 and abs(new_struct - struct_each) < 0.05:
            avail = total_area * PANEL_COVERAGE * PANEL_EFF * avg_irr * day_h
            margin = (avail - total_pwr * 24) / (total_pwr * 24)
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
                "N": N, "span": span, "AR": AR, "chord": chord,
                "area_each": area_each, "total_area": total_area,
                "struct_each": new_struct, "batt_each": new_batt,
                "ac_mass": ac, "fleet_mass": N * ac,
                "V_cruise": V_cruise,
                "total_power": total_pwr, "margin": margin,
                "cost": fc.total, "cost_breakdown": fc,
                "avail_Wh": avail, "day_h": day_h, "night_h": night_h,
            }

        batt_each = 0.7 * batt_each + 0.3 * new_batt
        struct_each = 0.7 * struct_each + 0.3 * new_struct

    return None


def daytime_payload_sweep(N, span, n_points=25):
    """Sweep daytime-only payload power from 0 to max (30% system margin).

    Daytime-only payload: powered only during the day; no additional night
    battery needed. This cleanly avoids the mass spiral and shows the
    platform's true payload capacity.

    Returns list of result dicts with varying payload_power.
    """
    base = _solve_base(N, span)
    if base is None:
        return []

    avail_Wh = base["avail_Wh"]
    day_h = base["day_h"]
    base_pwr = base["total_power"]

    # At 30% system margin: available for payload = avail/1.30 - base_pwr*24
    max_pld_energy_Wh = avail_Wh / (1 + TARGET_MARGIN) - base_pwr * 24
    if max_pld_energy_Wh <= 0:
        return [base]  # system already at margin with no payload

    max_pld_pwr = max_pld_energy_Wh / day_h

    rows = []
    for pld_pwr in np.linspace(0, max_pld_pwr, n_points):
        # Cost increases with payload power because solar panels must be sized
        # to support it + system needs, but aircraft mass is unchanged.
        # Here we add the payload power cost to the fleet cost.
        r = dict(base)
        r["payload_power"] = pld_pwr
        # Additional solar energy for payload: pld_pwr * day_h
        # => extra solar panel area needed (at avg irradiance)
        peak_irr = solar_irradiance(20000, LAT_DEG, DOY)
        avg_irr = (2 / np.pi) * peak_irr
        # Current solar panels already cover base + payload at 30% margin
        # Use existing panels, just report cost as-is (no new panels needed)
        r["effective_margin"] = (avail_Wh - (base_pwr + pld_pwr) * 24) / ((base_pwr + pld_pwr) * 24)
        rows.append(r)

    return rows


def main():
    print("Running cost vs payload sweep...\n")

    config_data = {}
    max_payloads = {}

    for label, N, span in CONFIGS:
        print(f"  {label}: sweeping daytime payload power...")
        rows = daytime_payload_sweep(N, span, n_points=25)
        if not rows:
            print(f"    -> no valid range found")
            continue
        config_data[label] = rows
        max_payloads[label] = rows[-1]["payload_power"]
        print(f"    -> max daytime payload = {max_payloads[label]:.0f} W @ 30% margin, "
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

    # Panel 4: Cost breakdown at 30% margin (stacked bar)
    ax = axes[1, 1]
    labels_at_max = []
    cb_list = []

    for label, rows in config_data.items():
        # Use the last row (at max payload power, closest to 30% margin)
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
    c_other  = np.array([c.assembly + c.ground_infra + c.tooling_amortized
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
    ax.set_title("Cost Breakdown at 30% Energy Margin")
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
