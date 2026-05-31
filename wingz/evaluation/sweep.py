"""
Parameter sweep engine. Composes all sub-models to evaluate a complete
aircraft or formation configuration.

The evaluator iterates to find a self-consistent solution where:
- Cruise speed is computed from wing loading (not hardcoded)
- Battery mass is included in total weight
- Total weight affects drag, which affects power, which affects battery
- Convergence means all quantities are mutually consistent

References:
    Cruise speed: V_cruise = margin * V_stall, where
    V_stall = sqrt(2W / (rho * S * CL_max))
    margin = stall_margin_day (1.15) or stall_margin_night (1.03)
    Ref: Anderson, Fundamentals of Aerodynamics, Ch. 5.

See docs/formation_flight/references.md for full citations.
"""

import enum
from dataclasses import dataclass, field
from itertools import product
from typing import Optional

import numpy as np

from wingz.aerodynamics.drag import induced_drag
from wingz.aerodynamics.formation_aero import (
    FormationGeometry, per_slot_drag_factor, effective_span,
)
from wingz.control.architectures import (
    FormationArchitecture, assign_roles, get_hardware_mass, get_hardware_power,
)
from wingz.control.station_keeping import station_keeping_power
from wingz.cost.mass_proxy import mass_proxy_cost
from wingz.mission.profiles import MissionProfile
from wingz.structures.beam import BeamStructure
from wingz.mission.payload import Payload, no_payload
from wingz.solar.energy_balance import (
    compute_energy_balance, required_battery_mass, required_coverage_fraction,
)
from wingz.structures.empirical import EmpiricalStructure, SOLAR_HALE_DATA


from wingz.constants import CL_MAX


class PositionStrategy(enum.Enum):
    HEAVY_FRONT = "heavy_front"
    HEAVY_WAKE = "heavy_wake"
    UNIFORM = "uniform"


@dataclass
class AircraftConfig:
    N: int
    span_each_m: float
    architecture: FormationArchitecture
    position_strategy: PositionStrategy
    geometry: FormationGeometry
    lateral_overlap_ratio: float
    aspect_ratio: Optional[float] = None  # if set, overrides wing_loading for area calc
    payload: Payload = field(default_factory=no_payload)


def _dynamic_pressure(rho: float, velocity: float) -> float:
    return 0.5 * rho * velocity**2


def evaluate_config(
    config: AircraftConfig,
    mission: MissionProfile,
    structure: Optional[EmpiricalStructure] = None,
    beam: Optional[BeamStructure] = None,
    latitude_deg: float = 30.0,
    day_of_year: int = 172,
    solar_margin: float = 3.0,       # panel area sized to produce margin × required energy
    max_panel_coverage: float = 0.90,  # can't panel more than 90% of wing
    panel_efficiency: float = 0.38,  # MicroLink III-V ELO, flight-proven on Zephyr/PHASA-35
    propulsion_efficiency: float = 0.75,  # combined prop × motor × ESC
    stall_margin_day: float = 1.15,   # V_cruise / V_stall during day
    stall_margin_night: float = 1.03,  # V_cruise / V_stall at night (calm stratosphere)
    night_descent_m: float = 0.0,     # altitude descent during night (gravity assist)
    max_iterations: int = 80,
) -> dict:
    """
    Evaluate a configuration with fully self-consistent mass convergence.

    Iterates until ALL of these converge simultaneously:
    - Structural mass (beam model: sized to carry actual loaded weight)
    - Battery mass (sized for night survival at actual power draw)
    - Cruise speed (from wing loading at actual total weight)
    - Drag and power (from actual speed and weight)

    The beam model replaces the empirical model when AR is set, because
    the empirical model was calibrated to empty aircraft and does not
    account for loaded weight.
    """
    structure = structure or EmpiricalStructure.from_data(SOLAR_HALE_DATA)
    beam = beam or BeamStructure()
    N = config.N
    span = config.span_each_m
    rho = mission.rho

    # Roles and hardware
    roles = assign_roles(config.architecture, N)
    hw_masses = [get_hardware_mass(config.architecture, r) for r in roles]
    hw_powers = [get_hardware_power(config.architecture, r) for r in roles]

    # Payload mass — distributed evenly across fleet
    payload_mass_each = config.payload.mass_kg / N

    # Wing area per aircraft (fixed by geometry)
    if config.aspect_ratio is not None:
        wing_area_each = span**2 / config.aspect_ratio
        ar_each = config.aspect_ratio
    else:
        # Legacy path: empirical structure, fixed velocity
        struct_init = structure.wing_mass(span, config.aspect_ratio)
        empty_weight = (struct_init + hw_masses[0] + payload_mass_each) * 9.81
        wing_area_each = mission.wing_area(empty_weight)
        ar_each = span**2 / wing_area_each if wing_area_each > 0 else 0

    total_wing_area = N * wing_area_each

    # Per-slot drag factors (fixed by geometry)
    drag_factors = per_slot_drag_factor(N, span, config.lateral_overlap_ratio, config.geometry)

    # Use beam model when AR is set (self-consistent structural sizing)
    use_beam = config.aspect_ratio is not None

    # Initialize iteration variables
    battery_mass_total = 0.0
    if use_beam:
        # Start with empirical estimate, will be replaced by beam
        struct_mass_each = structure.wing_mass(span, config.aspect_ratio)
    else:
        struct_mass_each = structure.wing_mass(span, config.aspect_ratio)

    for iteration in range(max_iterations):
        # Total mass per aircraft
        batt_each = battery_mass_total / N
        total_mass_per = [struct_mass_each + hw + payload_mass_each + batt_each
                          for hw in hw_masses]

        # Weight distribution
        total_fleet_mass = sum(total_mass_per)
        if total_fleet_mass <= 0:
            break
        total_weight = total_fleet_mass * 9.81
        weights = [m / total_fleet_mass * total_weight for m in total_mass_per]

        # Cruise speed (day margin for drag/power calculations)
        max_weight = max(weights)
        if use_beam:
            v_stall = np.sqrt(2 * max_weight / (rho * wing_area_each * CL_MAX))
            velocity = stall_margin_day * v_stall
        else:
            velocity = mission.velocity
            v_stall = velocity / stall_margin_day
        q = _dynamic_pressure(rho, velocity)

        # Position strategy reordering
        w_ordered = list(weights)
        hp_ordered = list(hw_powers)
        hm_ordered = list(hw_masses)

        if N > 1 and config.position_strategy == PositionStrategy.HEAVY_WAKE:
            mass_order = np.argsort(total_mass_per)
            factor_order = np.argsort(drag_factors)[::-1]
            slot_assignment = [0] * N
            for rank, aircraft_idx in enumerate(mass_order):
                slot_assignment[aircraft_idx] = factor_order[rank]
            w_new = [0.0] * N
            hp_new = [0.0] * N
            hm_new = [0.0] * N
            for aircraft_idx in range(N):
                slot = slot_assignment[aircraft_idx]
                w_new[slot] = weights[aircraft_idx]
                hp_new[slot] = hw_powers[aircraft_idx]
                hm_new[slot] = hw_masses[aircraft_idx]
            w_ordered, hp_ordered, hm_ordered = w_new, hp_new, hm_new
        elif N > 1 and config.position_strategy == PositionStrategy.HEAVY_FRONT:
            mass_order = list(np.argsort(total_mass_per)[::-1])
            w_ordered = [weights[i] for i in mass_order]
            hp_ordered = [hw_powers[i] for i in mass_order]
            hm_ordered = [hw_masses[i] for i in mass_order]

        # Per-slot drag
        total_induced = 0.0
        total_parasite = 0.0
        for i in range(N):
            di = drag_factors[i] * w_ordered[i]**2 / (
                q * np.pi * mission.oswald_e * span**2)
            dp = q * wing_area_each * mission.cd0
            total_induced += di
            total_parasite += dp

        total_drag = total_induced + total_parasite

        # Station-keeping power
        sk_total = 0.0
        for i in range(N):
            is_leader = (i == 0 and N > 1) or N == 1
            sk = station_keeping_power(
                mission=mission, span_m=span,
                position_tolerance_m=2.0, is_leader=is_leader)
            sk_total += sk

        # Day power (at day stall margin)
        thrust_power = total_drag * velocity
        propulsion_power = thrust_power / propulsion_efficiency
        total_hw_power = sum(hp_ordered)
        total_payload_power = config.payload.power_W
        total_power_day = propulsion_power + total_hw_power + sk_total + total_payload_power

        # Night power (at night stall margin, lower speed)
        v_night = stall_margin_night * v_stall
        q_night = _dynamic_pressure(rho, v_night)
        night_induced = 0.0
        night_parasite = 0.0
        for i in range(N):
            di = drag_factors[i] * w_ordered[i]**2 / (
                q_night * np.pi * mission.oswald_e * span**2)
            dp = q_night * wing_area_each * mission.cd0
            night_induced += di
            night_parasite += dp
        night_drag = night_induced + night_parasite
        night_thrust = night_drag * v_night
        night_propulsion = night_thrust / propulsion_efficiency

        # Night descent gravity assist
        night_hours = energy_result.night_hours if iteration > 0 else 10.1
        if night_descent_m > 0 and night_hours > 0:
            descent_rate = night_descent_m / (night_hours * 3600)
            gravity_power = total_fleet_mass * 9.81 * descent_rate / propulsion_efficiency
        else:
            gravity_power = 0.0

        total_power_night = max(0, night_propulsion - gravity_power) + total_hw_power + sk_total + total_payload_power

        # Use day power for energy balance (solar collection vs day consumption)
        # Use night power for battery sizing
        total_power = total_power_day  # for backwards compat in results

        # Compute total 24h energy requirement for panel sizing
        day_hours_est = energy_result.day_hours if iteration > 0 else 13.9
        night_hours_est = 24.0 - day_hours_est
        energy_required_24h = total_power_day * day_hours_est + total_power_night * night_hours_est

        # Size panel coverage to produce margin × required energy
        panel_coverage = required_coverage_fraction(
            energy_required_Wh=energy_required_24h,
            solar_margin=solar_margin,
            wing_area_m2=total_wing_area,
            panel_efficiency=panel_efficiency,
            altitude_m=mission.altitude_m,
            latitude_deg=latitude_deg,
            day_of_year=day_of_year,
            max_coverage=max_panel_coverage,
        )

        # Energy balance with computed coverage
        energy_result = compute_energy_balance(
            power_required_W=total_power_day,
            wing_area_m2=total_wing_area,
            coverage_fraction=panel_coverage,
            panel_efficiency=panel_efficiency,
            altitude_m=mission.altitude_m,
            latitude_deg=latitude_deg,
            day_of_year=day_of_year,
        )

        new_battery_mass = required_battery_mass(
            power_required_W=total_power_night,
            night_hours=energy_result.night_hours,
        )

        # Update structural mass from beam model (sized to actual loaded weight)
        if use_beam:
            # Each aircraft's structure must carry its own loaded weight
            ac_mass_for_struct = max(total_mass_per)
            new_struct = beam.wing_mass(span, ar_each, ac_mass_for_struct)
        else:
            new_struct = struct_mass_each  # empirical, doesn't change

        # Check convergence (both battery and structure must settle)
        batt_converged = abs(new_battery_mass - battery_mass_total) < 0.1
        struct_converged = abs(new_struct - struct_mass_each) < 0.1

        if batt_converged and struct_converged:
            break

        # Detect divergence: if mass is growing without bound, stop
        if new_battery_mass > 1e6 or new_struct > 1e6 or not np.isfinite(new_battery_mass):
            # Mark as diverged — results will show NaN/huge values
            battery_mass_total = float('nan')
            struct_mass_each = float('nan')
            break

        # Damped update for stability
        battery_mass_total = 0.6 * battery_mass_total + 0.4 * new_battery_mass
        struct_mass_each = 0.6 * struct_mass_each + 0.4 * new_struct

    # Final values
    control_mass_total = sum(hm_ordered)
    cost_score = mass_proxy_cost(
        structural_mass_kg=N * struct_mass_each,
        control_mass_kg=control_mass_total, N=N)
    b_eff = effective_span(N, span, config.lateral_overlap_ratio, config.geometry)

    # Wing loading and stall speed
    wing_loading = max(weights) / wing_area_each if wing_area_each > 0 else 0
    v_stall = np.sqrt(2 * max(weights) / (rho * wing_area_each * CL_MAX)) if wing_area_each > 0 else 0

    # Tip deflection from beam model
    deflection_pct = beam.deflection_percent(span, ar_each, max(total_mass_per)) if use_beam else 0

    return {
        "N": N,
        "span_each_m": span,
        "total_span_m": N * span,
        "effective_span_m": b_eff,
        "aspect_ratio": ar_each,
        "architecture": config.architecture.value,
        "position_strategy": config.position_strategy.value,
        "geometry": config.geometry.value,
        "lateral_overlap_ratio": config.lateral_overlap_ratio,
        "altitude_m": mission.altitude_m,
        "velocity_day_m_s": velocity,
        "velocity_night_m_s": v_night if use_beam else velocity,
        "v_stall_m_s": v_stall,
        "stall_margin_day": stall_margin_day,
        "stall_margin_night": stall_margin_night,
        "night_descent_m": night_descent_m,
        "wing_loading_N_m2": wing_loading,
        "wing_mass_each_kg": struct_mass_each,
        "wing_mass_total_kg": N * struct_mass_each,
        "control_mass_total_kg": control_mass_total,
        "payload_mass_kg": config.payload.mass_kg,
        "payload_power_W": config.payload.power_W,
        "battery_mass_kg": battery_mass_total,
        "total_mass_kg": total_fleet_mass,
        "total_mass_with_battery_kg": total_fleet_mass,  # battery already included
        "induced_drag_N": total_induced,
        "parasite_drag_N": total_parasite,
        "total_drag_N": total_drag,
        "thrust_power_W": thrust_power,
        "propulsion_power_W": propulsion_power,
        "propulsion_efficiency": propulsion_efficiency,
        "hw_power_W": total_hw_power,
        "sk_power_W": sk_total,
        "payload_power_total_W": total_payload_power,
        "total_power_day_W": total_power_day,
        "total_power_night_W": total_power_night,
        "total_power_W": total_power_day,  # backwards compat
        "total_wing_area_m2": total_wing_area,
        "panel_coverage": panel_coverage,
        "solar_margin": solar_margin,
        "cost_score": cost_score,
        "energy_available_Wh": energy_result.energy_available_Wh,
        "energy_required_Wh": energy_result.energy_required_total_Wh,
        "energy_surplus_Wh": energy_result.surplus_Wh,
        "energy_closes": energy_result.closes,
        "day_hours": energy_result.day_hours,
        "deflection_pct": deflection_pct,
        "iterations": iteration + 1,
        "mission": mission.name,
    }


def sweep_configs(
    spans: list,
    Ns: list,
    architectures: list,
    position_strategies: list,
    geometries: list,
    lateral_overlap_ratios: list,
    aspect_ratios: Optional[list] = None,
    payloads: Optional[list] = None,
) -> list:
    """Generate all combinations of sweep parameters.

    If aspect_ratios is None, AR is derived from span and wing loading.
    If payloads is None, no payload is included.
    """
    ar_list = aspect_ratios or [None]
    payload_list = payloads or [no_payload()]

    configs = []
    for span, N, arch, pos, geo, lor, ar, payload in product(
        spans, Ns, architectures, position_strategies, geometries,
        lateral_overlap_ratios, ar_list, payload_list,
    ):
        if N == 1:
            config = AircraftConfig(
                N=1, span_each_m=span, architecture=arch,
                position_strategy=PositionStrategy.UNIFORM, geometry=geo,
                lateral_overlap_ratio=0.0, aspect_ratio=ar, payload=payload,
            )
            if not any(
                c.N == 1 and c.span_each_m == span
                and c.aspect_ratio == ar and c.payload.name == payload.name
                for c in configs
            ):
                configs.append(config)
        else:
            configs.append(AircraftConfig(
                N=N, span_each_m=span, architecture=arch,
                position_strategy=pos, geometry=geo,
                lateral_overlap_ratio=lor, aspect_ratio=ar, payload=payload,
            ))
    return configs
