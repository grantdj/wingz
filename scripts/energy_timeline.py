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

from wingz.structures.beam import BeamStructure
from wingz.solar.power import solar_irradiance, day_length_hours, _solar_declination
from wingz.aerodynamics.formation_aero import per_slot_drag_factor, FormationGeometry

# ── constants ──────────────────────────────────────────────────────────────

G = 9.81
CL_MAX = 1.2
BATT_ENERGY_DENSITY = 250.0   # Wh/kg
PANEL_EFF = 0.38
PANEL_COVERAGE = 0.80
CD0 = 0.025
OSWALD_E = 0.85
CRUISE_ALT_M = 20000.0
RHO_CRUISE = 0.0889
LAT_DEG = 30.0
DOY = 172
V_CRUISE = 25.0  # m/s, fixed for these configs

# Configs: (label, N, span, AR_approx)
CONFIGS = [
    ("1x60m AR≈12.7", 1, 60, 12.7),
    ("2x40m AR≈11.2", 2, 40, 11.2),
    ("4x20m AR≈8.3",  4, 20,  8.3),
    ("6x10m AR≈6.4",  6, 10,  6.4),
]

COLORS = ["#2196F3", "#4CAF50", "#FF9800", "#E91E63"]


# ── solver (fixed-AR geometry, same approach as converged_sweep.py) ────────

def _choose_ar(span):
    """Pick a realistic design AR for a given span (6-14 range per spec)."""
    ar = 5.0 + span / 6.0
    return float(np.clip(ar, 6.0, 14.0))


def solve(N, span, AR=None, pld_power=0, pld_g_per_W=50):
    """Fixed-AR self-consistent solver.

    Wing area = span² / AR (fixed geometry).
    Cruise speed from wing loading.
    Includes payload mass in convergence loop.
    """
    rho = RHO_CRUISE
    g = G
    hw = 2.5
    pld_mass_each = pld_power * pld_g_per_W / 1000 / N

    if AR is None:
        AR = _choose_ar(span)

    # Fixed wing geometry
    area_each = span ** 2 / AR
    factors = per_slot_drag_factor(N, span, 0.1, FormationGeometry.V)

    day_h = day_length_hours(LAT_DEG, DOY)
    night_h = 24 - day_h
    hw_pwr = 15 + 3 * (N - 1)
    sk_total = 5.0 * max(0, N - 1)

    struct_each = 5.0
    batt_each = 5.0
    beam = BeamStructure()

    for _ in range(300):
        ac = struct_each + hw + pld_mass_each + batt_each
        W = ac * g

        # Cruise speed from wing loading (self-consistent)
        V_cruise = 1.3 * np.sqrt(2 * W / (rho * area_each * CL_MAX))
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

        if abs(new_batt - batt_each) < 0.05 and abs(new_struct - struct_each) < 0.05:
            return {
                "N": N, "span": span, "V_cruise": V_cruise,
                "area_each": area_each, "AR": AR,
                "struct_each": new_struct, "batt_each": new_batt,
                "ac_mass": ac,
                "total_power": total_pwr,
                "batt_capacity_Wh": new_batt * BATT_ENERGY_DENSITY,
                "day_h": day_h, "night_h": night_h,
            }

        batt_each = 0.7 * batt_each + 0.3 * new_batt
        struct_each = 0.7 * struct_each + 0.3 * new_struct

    return None


def _solar_power_instant(total_area_m2, alt_m, t_h):
    """Instantaneous solar power for formation (W) at time-of-day t_h."""
    solar_noon_h = 12.0
    hour_angle = np.radians((t_h - solar_noon_h) * 15.0)
    declination = _solar_declination(DOY)
    lat_rad = np.radians(LAT_DEG)
    sin_el = (np.sin(lat_rad) * np.sin(declination)
              + np.cos(lat_rad) * np.cos(declination) * np.cos(hour_angle))
    if sin_el <= 0.0:
        return 0.0
    tau = 0.3 * np.exp(-alt_m / 8500)
    irr = 1361.0 * np.exp(-tau / max(sin_el, 0.01))
    return total_area_m2 * PANEL_COVERAGE * PANEL_EFF * irr


def simulate_24h(cfg_dict):
    """
    Simulate one 24h cycle at cruise altitude starting at dawn with empty battery.

    Returns time arrays and power/energy arrays.
    """
    c = cfg_dict
    N = c["N"]
    total_area = N * c["area_each"]
    batt_cap_Wh = c["batt_capacity_Wh"]
    req_pwr = c["total_power"]   # required power (W), total formation

    day_h = c["day_h"]
    sunrise_h = 12.0 - day_h / 2.0

    dt_min = 10
    dt_h = dt_min / 60.0
    n_steps = int(24.0 / dt_h)

    time_h = np.zeros(n_steps)
    solar_W = np.zeros(n_steps)
    req_W = np.zeros(n_steps)
    batt_Wh = np.zeros(n_steps)
    waste_W = np.zeros(n_steps)

    batt = 0.0  # start empty (worst case)

    for i in range(n_steps):
        t = sunrise_h + i * dt_h   # 0 = dawn
        t_local = t % 24.0
        time_h[i] = t - sunrise_h  # hours from dawn

        sol = _solar_power_instant(total_area, CRUISE_ALT_M, t_local)
        solar_W[i] = sol
        req_W[i] = req_pwr

        net = sol - req_pwr
        if net > 0:
            headroom = batt_cap_Wh - batt
            to_batt = min(net * dt_h, headroom)
            waste_W[i] = max(0, net - headroom / dt_h) if headroom / dt_h < net else 0.0
            batt += to_batt
        else:
            batt = max(0.0, batt + net * dt_h)

        batt_Wh[i] = batt

    return {
        "time_h": time_h,
        "solar_W": solar_W,
        "req_W": req_W,
        "batt_Wh": batt_Wh,
        "batt_pct": batt_Wh / batt_cap_Wh * 100,
        "waste_W": waste_W,
        "day_h": day_h,
    }


def _find_payload_for_margin(N, span, target_margin=0.30):
    """Binary search for payload power that gives target energy margin."""
    peak_irr = solar_irradiance(CRUISE_ALT_M, LAT_DEG, DOY)
    day_h = day_length_hours(LAT_DEG, DOY)
    avg_irr = (2 / np.pi) * peak_irr

    lo, hi = 0, 20000
    for _ in range(45):
        mid = (lo + hi) / 2
        r = solve(N, span, pld_power=mid)
        if r is None:
            hi = mid
            continue
        avail = N * r["area_each"] * PANEL_COVERAGE * PANEL_EFF * avg_irr * day_h
        margin = (avail - r["total_power"] * 24) / (r["total_power"] * 24)
        if margin > target_margin:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main():
    print("Simulating 24h energy profiles at cruise altitude...")
    print("Finding payload for 30% energy margin, then simulating 24h cycle.\n")

    datasets = []
    for label, N, span, ar_approx in CONFIGS:
        # Find payload at 30% margin
        pld_pwr = _find_payload_for_margin(N, span, target_margin=0.30)
        r = solve(N, span, pld_power=pld_pwr)
        if r is None:
            print(f"  {label}: FAILED TO CONVERGE")
            continue
        sim = simulate_24h(r)
        sim["label"] = label
        sim["N"] = N
        sim["span"] = span
        datasets.append(sim)
        print(f"  {label}: pld={pld_pwr:.0f}W, req={r['total_power']:.0f}W, "
              f"batt_cap={r['batt_capacity_Wh']:.0f}Wh/ac, ac={r['ac_mass']:.0f}kg, AR={r['AR']:.1f}")

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
