"""
Parameter sweep engine. Composes all sub-models to evaluate a complete
aircraft or formation configuration.

The evaluator iterates to find a self-consistent solution where:
- Cruise speed is computed from wing loading (not hardcoded)
- Battery mass is included in total weight
- Total weight affects drag, which affects power, which affects battery
- Convergence means all quantities are mutually consistent

References:
    Cruise speed: V_cruise = 1.3 * V_stall, where
    V_stall = sqrt(2W / (rho * S * CL_max))
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
from wingz.mission.payload import Payload, no_payload
from wingz.solar.energy_balance import compute_energy_balance, required_battery_mass
from wingz.structures.empirical import EmpiricalStructure, SOLAR_HALE_DATA


# Aerodynamic constants
CL_MAX = 1.2           # max lift coefficient for thin high-altitude airfoil
CL_CRUISE = 0.7        # cruise CL (corresponds to ~1.3x stall speed)
CRUISE_MARGIN = 1.3     # V_cruise / V_stall


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


def _cruise_speed(weight_N: float, wing_area_m2: float, rho: float) -> float:
    """
    Compute cruise speed from wing loading.

    V_stall = sqrt(2W / (rho * S * CL_max))
    V_cruise = 1.3 * V_stall

    Ref: Anderson (2017) Ch. 5.
    """
    if wing_area_m2 <= 0 or rho <= 0:
        return 25.0  # fallback
    v_stall = np.sqrt(2 * weight_N / (rho * wing_area_m2 * CL_MAX))
    return CRUISE_MARGIN * v_stall


def _dynamic_pressure(rho: float, velocity: float) -> float:
    return 0.5 * rho * velocity**2


def evaluate_config(
    config: AircraftConfig,
    mission: MissionProfile,
    structure: Optional[EmpiricalStructure] = None,
    latitude_deg: float = 30.0,
    day_of_year: int = 172,
    panel_coverage: float = 0.8,
    panel_efficiency: float = 0.38,  # MicroLink III-V ELO, flight-proven on Zephyr/PHASA-35
    max_iterations: int = 50,
) -> dict:
    """
    Evaluate a configuration with self-consistent cruise speed and battery mass.

    Iterates until total mass, cruise speed, drag, power, and battery mass
    all converge. The cruise speed is computed from wing loading at each
    iteration — not hardcoded.
    """
    structure = structure or EmpiricalStructure.from_data(SOLAR_HALE_DATA)
    N = config.N
    span = config.span_each_m
    rho = mission.rho

    # Roles and hardware
    roles = assign_roles(config.architecture, N)
    hw_masses = [get_hardware_mass(config.architecture, r) for r in roles]
    hw_powers = [get_hardware_power(config.architecture, r) for r in roles]

    # Structural mass per aircraft (AR-corrected if AR is set)
    struct_mass_each = structure.wing_mass(span, config.aspect_ratio)

    # Payload mass — distributed evenly across fleet
    payload_mass_each = config.payload.mass_kg / N

    # Wing area per aircraft (fixed by geometry, doesn't change with iteration)
    if config.aspect_ratio is not None:
        wing_area_each = span**2 / config.aspect_ratio
        ar_each = config.aspect_ratio
    else:
        # No AR specified: use wing loading to size wing area, then derive AR.
        # Wing area is sized to the empty aircraft weight (no battery) to avoid
        # feedback loop where bigger battery → more weight → more area → divergence.
        empty_weight = (struct_mass_each + hw_masses[0] + payload_mass_each) * 9.81
        wing_area_each = mission.wing_area(empty_weight)
        ar_each = span**2 / wing_area_each if wing_area_each > 0 else 0

    total_wing_area = N * wing_area_each

    # Per-slot drag factors (fixed by geometry)
    drag_factors = per_slot_drag_factor(N, span, config.lateral_overlap_ratio, config.geometry)

    # Iterate: battery mass affects total weight affects speed affects drag
    # affects power affects battery mass
    battery_mass_total = 0.0  # start with zero battery

    for iteration in range(max_iterations):
        # Total mass per aircraft (structure + hardware + payload + battery share)
        batt_each = battery_mass_total / N
        total_mass_per = [struct_mass_each + hw + payload_mass_each + batt_each
                          for hw in hw_masses]

        # Weight distribution
        total_fleet_mass = sum(total_mass_per)
        total_weight = total_fleet_mass * 9.81
        weights = [m / total_fleet_mass * total_weight for m in total_mass_per]

        # Cruise speed: compute from wing loading when AR is set (self-consistent),
        # otherwise use mission's fixed velocity (legacy behavior).
        max_weight = max(weights)
        if config.aspect_ratio is not None:
            velocity = _cruise_speed(max_weight, wing_area_each, rho)
        else:
            velocity = mission.velocity
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

        # Per-slot drag at computed cruise speed
        total_induced = 0.0
        total_parasite = 0.0
        for i in range(N):
            # Induced drag: D_i = factor * W^2 / (q * pi * e * b^2)
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

        # Power
        thrust_power = total_drag * velocity
        total_hw_power = sum(hp_ordered)
        total_payload_power = config.payload.power_W
        total_power = thrust_power + total_hw_power + sk_total + total_payload_power

        # Energy balance
        energy_result = compute_energy_balance(
            power_required_W=total_power,
            wing_area_m2=total_wing_area,
            coverage_fraction=panel_coverage,
            panel_efficiency=panel_efficiency,
            altitude_m=mission.altitude_m,
            latitude_deg=latitude_deg,
            day_of_year=day_of_year,
        )

        new_battery_mass = required_battery_mass(
            power_required_W=total_power,
            night_hours=energy_result.night_hours,
        )

        # Check convergence
        if abs(new_battery_mass - battery_mass_total) < 0.01:
            break

        # Damped update for stability
        battery_mass_total = 0.5 * battery_mass_total + 0.5 * new_battery_mass

    # Final values
    control_mass_total = sum(hm_ordered)
    cost_score = mass_proxy_cost(
        structural_mass_kg=N * struct_mass_each,
        control_mass_kg=control_mass_total, N=N)
    b_eff = effective_span(N, span, config.lateral_overlap_ratio, config.geometry)

    # Wing loading
    wing_loading = max(weights) / wing_area_each

    # Stall speed
    v_stall = np.sqrt(2 * max(weights) / (rho * wing_area_each * CL_MAX))

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
        "velocity_m_s": velocity,
        "v_stall_m_s": v_stall,
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
        "hw_power_W": total_hw_power,
        "sk_power_W": sk_total,
        "payload_power_total_W": total_payload_power,
        "total_power_W": total_power,
        "total_wing_area_m2": total_wing_area,
        "cost_score": cost_score,
        "energy_available_Wh": energy_result.energy_available_Wh,
        "energy_required_Wh": energy_result.energy_required_total_Wh,
        "energy_surplus_Wh": energy_result.surplus_Wh,
        "energy_closes": energy_result.closes,
        "day_hours": energy_result.day_hours,
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
