"""
Shared solver for formation flight analysis.

Provides the convergence loops and binary searches that all scripts need.
Uses wingz physics modules and constants — no hardcoded magic numbers.

Functions:
    solve_converged     — iterate struct + battery + speed to convergence
    find_max_payload    — binary search for max 24h-feasible payload power
    simulate_24h        — dawn-to-dawn battery simulation
    simulate_climb      — launch-to-altitude simulation
    solar_power_instant — instantaneous solar at a given hour and altitude
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional

from wingz.constants import (
    GRAVITY, CL_MAX, OSWALD_E, CD0,
    STALL_MARGIN_DAY, STALL_MARGIN_NIGHT,
    PANEL_EFFICIENCY, PANEL_COVERAGE, SOLAR_CONSTANT,
    BATTERY_ENERGY_DENSITY, PROPULSION_EFFICIENCY,
    PAYLOAD_SPECIFIC_MASS, CLIMB_POWER_FRACTION,
    DEFAULT_LATITUDE, DEFAULT_DAY_OF_YEAR,
    CRUISE_ALTITUDE_M, RHO_20KM,
    HARDWARE_POWER_LEADER, HARDWARE_POWER_FOLLOWER,
)
from wingz.structures.beam import BeamStructure
from wingz.solar.power import solar_irradiance, day_length_hours, _solar_declination
from wingz.aerodynamics.formation_aero import (
    per_slot_drag_factor, effective_span, FormationGeometry,
)
from wingz.cost.materials import fleet_cost, FleetCost
from wingz.mission.atmosphere import standard_atmosphere


def choose_ar(span: float, min_ar: float = 6.0, max_ar: float = 14.0) -> float:
    """Pick a realistic design AR for a given span."""
    ar = 5.0 + span / 6.0
    return float(np.clip(ar, min_ar, max_ar))


def _hw_power(N: int) -> float:
    """Total hardware power for N aircraft (1 leader + N-1 followers)."""
    return HARDWARE_POWER_LEADER + HARDWARE_POWER_FOLLOWER * (N - 1)


def _sk_power(N: int) -> float:
    """Simplified station-keeping power for N aircraft."""
    # Servo-based: ~3.75W per follower at light turbulence
    return 3.75 * max(0, N - 1)


def solar_power_instant(total_area_m2: float, alt_m: float, hour_of_day: float,
                        lat_deg: float = DEFAULT_LATITUDE,
                        doy: int = DEFAULT_DAY_OF_YEAR) -> float:
    """Instantaneous solar power (W) at a given hour of day and altitude."""
    ha = np.radians((hour_of_day - 12.0) * 15.0)
    dec = _solar_declination(doy)
    lat_rad = np.radians(lat_deg)
    sin_el = (np.sin(lat_rad) * np.sin(dec)
              + np.cos(lat_rad) * np.cos(dec) * np.cos(ha))
    if sin_el <= 0:
        return 0.0
    tau = 0.3 * np.exp(-alt_m / 8500)
    irr = SOLAR_CONSTANT * np.exp(-tau / max(sin_el, 0.01))
    return total_area_m2 * PANEL_COVERAGE * PANEL_EFFICIENCY * irr


def _level_power(W_per_ac: float, span: float, area_each: float,
                 rho: float, V: float, factors: list, N: int) -> float:
    """Total formation level-flight power (W) including propulsion efficiency."""
    q = 0.5 * rho * V ** 2
    drag = sum(
        factors[j] * W_per_ac ** 2 / (q * np.pi * OSWALD_E * span ** 2)
        + q * area_each * CD0
        for j in range(N)
    )
    return drag * V / PROPULSION_EFFICIENCY


def solve_converged(
    N: int,
    span: float,
    AR: Optional[float] = None,
    pld_power: float = 0.0,
    pld_g_per_W: float = PAYLOAD_SPECIFIC_MASS,
    lat_deg: float = DEFAULT_LATITUDE,
    doy: int = DEFAULT_DAY_OF_YEAR,
    rho: float = RHO_20KM,
    max_iter: int = 300,
) -> Optional[dict]:
    """
    Iterate structure + battery + speed to self-consistent convergence.

    Uses beam structural model, day/night stall margins, propulsion efficiency.
    Returns dict with all computed quantities, or None if diverged.
    """
    if AR is None:
        AR = choose_ar(span)

    beam = BeamStructure()
    area_each = span ** 2 / AR
    total_area = N * area_each
    factors = per_slot_drag_factor(N, span, 0.1, FormationGeometry.V)

    day_h = day_length_hours(lat_deg, doy)
    night_h = 24 - day_h
    avg_irr = (2 / np.pi) * solar_irradiance(CRUISE_ALTITUDE_M, lat_deg, doy)

    hw = 2.5  # mass-balanced
    hw_pwr = _hw_power(N)
    sk = _sk_power(N)
    pld_mass_each = pld_power * pld_g_per_W / 1000 / N

    struct_each = 5.0
    batt_each = 5.0

    for i in range(max_iter):
        ac = struct_each + hw + pld_mass_each + batt_each
        W = ac * GRAVITY

        # Day speed
        V_stall = np.sqrt(2 * W / (rho * area_each * CL_MAX))
        V_day = STALL_MARGIN_DAY * V_stall
        V_night = STALL_MARGIN_NIGHT * V_stall

        # Day power (for solar energy balance)
        P_day = _level_power(W, span, area_each, rho, V_day, factors, N) + hw_pwr + sk + pld_power

        # Night power (for battery sizing)
        P_night = _level_power(W, span, area_each, rho, V_night, factors, N) + hw_pwr + sk + pld_power

        new_batt = P_night * night_h / BATTERY_ENERGY_DENSITY / N
        new_struct = beam.wing_mass(span, AR, ac)

        if not np.isfinite(new_batt) or not np.isfinite(new_struct) or new_batt > 1e5:
            return None

        if abs(new_batt - batt_each) < 0.05 and abs(new_struct - struct_each) < 0.05 and i > 0:
            avail = total_area * PANEL_COVERAGE * PANEL_EFFICIENCY * avg_irr * day_h
            solar_surplus_ratio = (avail - P_day * 24) / (P_day * 24)
            b_eff = effective_span(N, span, 0.1, FormationGeometry.V)
            defl = beam.deflection_percent(span, AR, ac)

            fc = fleet_cost(
                N=N, structural_mass_kg=new_struct * N,
                solar_panel_area_m2=total_area,
                battery_capacity_kWh=new_batt * N * BATTERY_ENERGY_DENSITY / 1000,
                span_m=span, n_full_nav=1, n_basic_nav=N - 1,
                production_run=10,
            )

            return {
                "N": N, "span": span, "AR": AR,
                "chord": span / AR, "area_each": area_each,
                "struct_each": new_struct, "batt_each": new_batt,
                "ac_mass": ac, "fleet_mass": N * ac,
                "V_stall": V_stall, "V_day": V_day, "V_night": V_night,
                "wing_loading": W / area_each,
                "P_day": P_day, "P_night": P_night,
                "solar_surplus_ratio": solar_surplus_ratio,
                "effective_span": b_eff, "deflection_pct": defl,
                "payload_power": pld_power,
                "payload_mass_each": pld_mass_each,
                "payload_mass_total": pld_mass_each * N,
                "cost": fc.total, "cost_breakdown": fc,
                "iterations": i + 1,
            }

        batt_each = 0.7 * batt_each + 0.3 * new_batt
        struct_each = 0.7 * struct_each + 0.3 * new_struct

    return None


def find_max_payload(
    N: int,
    span: float,
    AR: Optional[float] = None,
    pld_g_per_W: float = PAYLOAD_SPECIFIC_MASS,
    max_search: float = 20000.0,
    n_steps: int = 45,
    **kwargs,
) -> Optional[dict]:
    """
    Binary search for max continuous payload power that remains 24h-feasible.

    Returns the converged result dict at max payload, or None.
    """
    lo, hi = 0.0, max_search
    best = None

    for _ in range(n_steps):
        mid = (lo + hi) / 2
        result = solve_converged(N, span, AR=AR, pld_power=mid,
                                 pld_g_per_W=pld_g_per_W, **kwargs)
        if result is None or result["solar_surplus_ratio"] < 0:
            hi = mid
        else:
            lo = mid
            best = result

    if best is None:
        best = solve_converged(N, span, AR=AR, pld_power=0.0,
                               pld_g_per_W=pld_g_per_W, **kwargs)
    return best


def simulate_24h(
    total_area: float,
    batt_cap_Wh: float,
    power_required: float,
    alt_m: float = CRUISE_ALTITUDE_M,
    lat_deg: float = DEFAULT_LATITUDE,
    doy: int = DEFAULT_DAY_OF_YEAR,
    dt_min: float = 10,
) -> dict:
    """
    Simulate one 24h cycle starting at dawn with empty battery.

    Returns dict with time_h, solar_W, req_W, batt_Wh, batt_pct, waste_W arrays.
    """
    day_h = day_length_hours(lat_deg, doy)
    sunrise_h = 12.0 - day_h / 2.0
    dt_h = dt_min / 60.0
    n_steps = int(24.0 / dt_h)

    time_h = np.zeros(n_steps)
    solar_W = np.zeros(n_steps)
    req_W = np.zeros(n_steps)
    batt_Wh = np.zeros(n_steps)
    waste_W = np.zeros(n_steps)

    batt = 0.0

    for i in range(n_steps):
        t = sunrise_h + i * dt_h
        t_local = t % 24.0
        time_h[i] = t - sunrise_h

        sol = solar_power_instant(total_area, alt_m, t_local, lat_deg, doy)
        solar_W[i] = sol
        req_W[i] = power_required

        net = sol - power_required
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
        "batt_pct": batt_Wh / batt_cap_Wh * 100 if batt_cap_Wh > 0 else np.zeros(n_steps),
        "waste_W": waste_W,
        "day_h": day_h,
    }


def simulate_climb(
    N: int,
    span: float,
    AR: Optional[float] = None,
    target_alt: float = CRUISE_ALTITUDE_M,
    total_h: float = 48,
    dt_min: float = 6,
    lat_deg: float = DEFAULT_LATITUDE,
    doy: int = DEFAULT_DAY_OF_YEAR,
) -> dict:
    """
    Simulate launch-to-altitude. Start at sea level, sunrise, full battery.

    Returns dict with time, altitude, battery, solar, power arrays plus metadata.
    """
    if AR is None:
        AR = choose_ar(span)

    beam = BeamStructure()
    factors = per_slot_drag_factor(N, span, 0.1, FormationGeometry.V)
    area_each = span ** 2 / AR
    total_area = N * area_each
    hw = 2.5
    hw_pwr = _hw_power(N)

    # Converge at cruise altitude for battery sizing
    rho_cruise = standard_atmosphere(target_alt).rho
    struct_each = 5.0
    batt_each = 5.0
    day_h = day_length_hours(lat_deg, doy)
    night_h = 24 - day_h

    for _ in range(300):
        ac = struct_each + hw + batt_each
        W = ac * GRAVITY
        V_stall = np.sqrt(2 * W / (rho_cruise * area_each * CL_MAX))
        V_night = max(STALL_MARGIN_NIGHT * V_stall, 3.0)
        pwr_night = _level_power(W, span, area_each, rho_cruise, V_night, factors, N) + hw_pwr
        new_batt = pwr_night * night_h / BATTERY_ENERGY_DENSITY / N
        new_struct = beam.wing_mass(span, AR, ac)
        if not np.isfinite(new_batt) or new_batt > 1e5:
            break
        if abs(new_batt - batt_each) < 0.05 and abs(new_struct - struct_each) < 0.05:
            break
        batt_each = 0.7 * batt_each + 0.3 * new_batt
        struct_each = 0.7 * struct_each + 0.3 * new_struct

    batt_cap_Wh = batt_each * BATTERY_ENERGY_DENSITY
    ac_mass = struct_each + hw + batt_each
    sunrise_h = 12.0 - day_h / 2.0

    # Simulation
    dt_h = dt_min / 60.0
    n_steps = int(total_h / dt_h)

    time_arr = np.zeros(n_steps)
    alt_arr = np.zeros(n_steps)
    batt_arr = np.zeros(n_steps)
    solar_arr = np.zeros(n_steps)
    lvl_pwr_arr = np.zeros(n_steps)

    alt = 0.0
    batt_Wh = batt_cap_Wh
    dead = False

    for step in range(n_steps):
        t_h = sunrise_h + step * dt_h
        time_arr[step] = t_h

        if dead:
            alt_arr[step] = alt_arr[step - 1] if step > 0 else 0.0
            batt_arr[step] = 0.0
            continue

        atm = standard_atmosphere(alt)
        rho = atm.rho
        W = ac_mass * GRAVITY
        V_stall_local = np.sqrt(2 * W / (rho * area_each * CL_MAX))

        t_local = t_h % 24.0
        sol_pwr = solar_power_instant(total_area, alt, t_local, lat_deg, doy)
        is_day = sol_pwr > 0
        V = max(V_stall_local * (STALL_MARGIN_DAY if is_day else STALL_MARGIN_NIGHT), 5.0)

        lvl_pwr = _level_power(W, span, area_each, rho, V, factors, N) + hw_pwr

        net = sol_pwr - lvl_pwr

        if sol_pwr > 0 and alt < target_alt:
            surplus = max(net, 0)
            to_climb = surplus * CLIMB_POWER_FRACTION
            to_batt = surplus * (1 - CLIMB_POWER_FRACTION)
            climb_rate = to_climb / (ac_mass * N * GRAVITY) if ac_mass * N * GRAVITY > 0 else 0
            alt = min(alt + climb_rate * dt_h * 3600, target_alt)
            batt_Wh = min(batt_Wh + to_batt * dt_h, batt_cap_Wh)
        elif net > 0:
            batt_Wh = min(batt_Wh + net * dt_h, batt_cap_Wh)
        else:
            deficit_Wh = abs(net) * dt_h
            batt_Wh -= deficit_Wh / N
            if batt_Wh <= 0:
                batt_Wh = 0.0
                dead = True

        alt_arr[step] = alt
        batt_arr[step] = batt_Wh / batt_cap_Wh * 100 if batt_cap_Wh > 0 else 0
        solar_arr[step] = sol_pwr
        lvl_pwr_arr[step] = lvl_pwr

    return {
        "time_h": time_arr,
        "alt_m": alt_arr,
        "batt_pct": batt_arr,
        "solar_W": solar_arr,
        "lvl_pwr_W": lvl_pwr_arr,
        "ac_mass": ac_mass,
        "batt_cap_Wh": batt_cap_Wh,
        "struct_each": struct_each,
        "batt_each": batt_each,
        "AR": AR,
        "max_alt_reached": float(np.max(alt_arr)),
        "reached_target": float(np.max(alt_arr)) >= target_alt * 0.99,
        "sunrise_h": sunrise_h,
        "day_h": day_h,
    }
