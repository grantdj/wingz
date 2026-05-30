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

from wingz.structures.beam import BeamStructure
from wingz.solar.power import solar_irradiance, day_length_hours, _solar_declination
from wingz.aerodynamics.formation_aero import per_slot_drag_factor, FormationGeometry
from wingz.mission.atmosphere import standard_atmosphere

# ── constants ──────────────────────────────────────────────────────────────

G = 9.81
CL_MAX = 1.2
BATT_ENERGY_DENSITY = 250.0   # Wh/kg
PANEL_EFF = 0.38
PANEL_COVERAGE = 0.80
CD0 = 0.025
OSWALD_E = 0.85
CRUISE_ALT_M = 20000.0
LAT_DEG = 30.0
DOY = 172                      # summer solstice-ish


def _parse_args():
    p = argparse.ArgumentParser(description="Climb profile simulation")
    p.add_argument("--N", type=int, default=2, help="Number of aircraft")
    p.add_argument("--span", type=float, default=40.0, help="Span per aircraft (m)")
    p.add_argument("--save", action="store_true")
    return p.parse_args()


def _stall_speed(W_N, area_m2, rho):
    return np.sqrt(2 * W_N / (rho * area_m2 * CL_MAX))


def _level_power(W_N, span, area_m2, rho, V, factors, N):
    q = 0.5 * rho * V ** 2
    drag = sum(
        factors[j] * W_N ** 2 / (q * np.pi * OSWALD_E * span ** 2)
        + q * area_m2 * CD0
        for j in range(N)
    )
    return drag * V  # watts, total for formation


def _solar_power_at(alt_m, total_area_m2, time_h):
    """Instantaneous solar power at given hour of day (0=midnight)."""
    # Hour angle relative to solar noon
    solar_noon_h = 12.0
    hour_angle = np.radians((time_h - solar_noon_h) * 15.0)

    declination = _solar_declination(DOY)
    lat_rad = np.radians(LAT_DEG)
    sin_el = (np.sin(lat_rad) * np.sin(declination)
              + np.cos(lat_rad) * np.cos(declination) * np.cos(hour_angle))
    sin_el = max(sin_el, 0.0)  # below horizon → 0

    if sin_el <= 0.0:
        return 0.0

    scale_height = 8500.0
    tau_sl = 0.3
    tau = tau_sl * np.exp(-alt_m / scale_height)
    airmass = 1.0 / max(sin_el, 0.01)
    irr = 1361.0 * np.exp(-tau * airmass)

    return total_area_m2 * PANEL_COVERAGE * PANEL_EFF * irr


def _choose_ar(span):
    """Pick a realistic design AR for a given span (6-14 range)."""
    ar = 5.0 + span / 6.0
    return float(np.clip(ar, 6.0, 14.0))


def simulate(N, span, dt_min=6, total_h=48):
    """Run the climb simulation. Returns dict of time-series arrays."""
    beam = BeamStructure()
    factors = per_slot_dag_factor_cached(N, span)

    # ── design AR (fixed geometry, not derived from weight) ──
    AR = _choose_ar(span)
    area_each = span ** 2 / AR  # fixed wing area from geometry
    chord = span / AR

    hw_per_ac = 2.5   # kg
    hw_pwr = 15 + 3 * (N - 1)  # W, hardware power

    # Converge structure + battery at cruise altitude
    rho_cruise = standard_atmosphere(CRUISE_ALT_M).rho
    struct_each = 5.0
    batt_each = 5.0

    day_h = day_length_hours(LAT_DEG, DOY)
    night_h = 24 - day_h

    for _ in range(300):
        ac = struct_each + hw_per_ac + batt_each
        W_cruise = ac * G

        # Cruise speed from wing loading (self-consistent)
        V_cruise = 1.3 * np.sqrt(2 * W_cruise / (rho_cruise * area_each * CL_MAX))
        V_cruise = max(V_cruise, 3.0)

        pwr_cruise = _level_power(W_cruise, span, area_each, rho_cruise, V_cruise, factors, N)
        total_pwr = pwr_cruise + hw_pwr
        new_batt = total_pwr * night_h / BATT_ENERGY_DENSITY / N
        new_struct = beam.wing_mass(span, AR, ac)

        if not np.isfinite(new_batt) or not np.isfinite(new_struct) or new_batt > 1e5:
            break

        if abs(new_batt - batt_each) < 0.05 and abs(new_struct - struct_each) < 0.05:
            break
        batt_each = 0.7 * batt_each + 0.3 * new_batt
        struct_each = 0.7 * struct_each + 0.3 * new_struct

    batt_capacity_Wh = batt_each * BATT_ENERGY_DENSITY  # Wh per aircraft
    ac_mass = struct_each + hw_per_ac + batt_each
    wing_area_each = area_each  # fixed from design AR

    # ── time-stepping simulation ──────────────────────────────────────────
    dt_h = dt_min / 60.0
    n_steps = int(total_h / dt_h)

    # Start at sunrise
    day_h = day_length_hours(LAT_DEG, DOY)
    sunrise_h = 12.0 - day_h / 2.0

    time_arr = np.zeros(n_steps)
    alt_arr = np.zeros(n_steps)
    batt_arr = np.zeros(n_steps)   # Wh per aircraft
    solar_arr = np.zeros(n_steps)  # W total formation
    lvl_pwr_arr = np.zeros(n_steps)  # W total formation

    alt = 0.0
    batt_Wh = batt_capacity_Wh  # start full
    dead = False

    for step in range(n_steps):
        t_h = sunrise_h + step * dt_h
        time_arr[step] = t_h

        if dead:
            alt_arr[step] = alt_arr[step - 1] if step > 0 else 0.0
            batt_arr[step] = 0.0
            solar_arr[step] = 0.0
            lvl_pwr_arr[step] = lvl_pwr_arr[step - 1] if step > 0 else 0.0
            continue

        atm = standard_atmosphere(alt)
        rho = atm.rho

        # Wing area (fixed from initial sizing), adjust V for current density
        W_N = ac_mass * G
        # cruise speed at current density (constant wing loading)
        V = np.sqrt(2 * W_N / (rho * wing_area_each * CL_MAX)) * 1.3 / np.sqrt(1.3)
        V = max(V, 5.0)

        total_area = N * wing_area_each
        lvl_pwr = _level_power(W_N, span, wing_area_each, rho, V, factors, N) + hw_pwr

        # Hour of day (wrap to 0-24)
        t_local = t_h % 24.0
        sol_pwr = _solar_power_at(alt, total_area, t_local)

        net = sol_pwr - lvl_pwr

        if sol_pwr > 0 and alt < CRUISE_ALT_M:
            # Climb: 80% of surplus to climb, 20% to battery
            surplus = max(net, 0)
            to_climb = surplus * 0.80
            to_batt = surplus * 0.20

            # Climb rate from excess power (all N aircraft)
            climb_power = to_climb  # W
            climb_rate = climb_power / (ac_mass * N * G) if ac_mass * N * G > 0 else 0
            alt = min(alt + climb_rate * dt_h * 3600, CRUISE_ALT_M)

            batt_Wh = min(batt_Wh + to_batt * dt_h, batt_capacity_Wh)
        elif net > 0:
            # At cruise alt or no climb surplus — charge
            batt_Wh = min(batt_Wh + net * dt_h, batt_capacity_Wh)
        else:
            # Deficit — drain battery
            deficit_Wh = abs(net) * dt_h
            batt_Wh -= deficit_Wh / N  # per-aircraft drain
            if batt_Wh <= 0:
                batt_Wh = 0.0
                dead = True

        time_arr[step] = t_h
        alt_arr[step] = alt
        batt_arr[step] = batt_Wh
        solar_arr[step] = sol_pwr
        lvl_pwr_arr[step] = lvl_pwr

    return {
        "time_h": time_arr,
        "alt_m": alt_arr,
        "batt_pct": batt_arr / batt_capacity_Wh * 100,
        "solar_W": solar_arr,
        "level_pwr_W": lvl_pwr_arr,
        "batt_capacity_Wh": batt_capacity_Wh,
        "ac_mass": ac_mass,
        "day_h": day_h,
        "sunrise_h": sunrise_h,
    }


def per_slot_dag_factor_cached(N, span):
    return per_slot_drag_factor(N, span, 0.1, FormationGeometry.V)


def _night_spans(time_h, day_h, sunrise_h):
    """Return list of (t_start, t_end) night intervals for shading."""
    spans = []
    t_min, t_max = time_h[0], time_h[-1]
    sunset_h = sunrise_h + day_h

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
    data = simulate(N, span)

    print(f"  Aircraft mass: {data['ac_mass']:.2f} kg/ac")
    print(f"  Battery capacity: {data['batt_capacity_Wh']:.1f} Wh/ac")
    max_alt = data["alt_m"].max()
    print(f"  Max altitude reached: {max_alt/1000:.1f} km")
    cruise_reached = np.any(data["alt_m"] >= CRUISE_ALT_M * 0.99)
    print(f"  Cruise altitude reached: {cruise_reached}")

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
    ax.axhline(CRUISE_ALT_M / 1000, color="red", ls="--", lw=1, label="Target (20km)")
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
    ax.plot(t, data["level_pwr_W"] / 1000, color="#F44336", lw=2, label="Level flight power")
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
