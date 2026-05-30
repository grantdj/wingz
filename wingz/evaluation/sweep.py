"""
Parameter sweep engine. Composes all sub-models to evaluate a complete
aircraft or formation configuration.
"""

import enum
from dataclasses import dataclass, field
from itertools import product
from typing import Optional

import numpy as np

from wingz.aerodynamics.drag import induced_drag, parasite_drag
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


def _wing_area_from_config(config: AircraftConfig, weight_N: float, mission: MissionProfile) -> float:
    """Compute wing area. If AR is set, use S = b^2/AR. Otherwise use wing loading."""
    if config.aspect_ratio is not None:
        return config.span_each_m**2 / config.aspect_ratio
    return mission.wing_area(weight_N)


def evaluate_config(
    config: AircraftConfig,
    mission: MissionProfile,
    structure: Optional[EmpiricalStructure] = None,
    latitude_deg: float = 30.0,
    day_of_year: int = 172,
    panel_coverage: float = 0.8,
    panel_efficiency: float = 0.25,
) -> dict:
    structure = structure or EmpiricalStructure.from_data(SOLAR_HALE_DATA)
    N = config.N
    span = config.span_each_m

    # Roles and hardware
    roles = assign_roles(config.architecture, N)
    hw_masses = [get_hardware_mass(config.architecture, r) for r in roles]
    hw_powers = [get_hardware_power(config.architecture, r) for r in roles]

    # Structural mass per aircraft
    struct_mass_each = structure.wing_mass(span)

    # Payload mass — distributed evenly across fleet for now
    payload_mass_each = config.payload.mass_kg / N
    payload_power_each = config.payload.power_W / N

    # Total mass per aircraft (structure + hardware + payload share)
    total_mass_per = [struct_mass_each + hw + payload_mass_each for hw in hw_masses]

    # Weight distribution
    total_fleet_mass = sum(total_mass_per)
    total_weight = total_fleet_mass * 9.81
    weights = [m / total_fleet_mass * total_weight for m in total_mass_per]

    # Per-slot drag factors
    drag_factors = per_slot_drag_factor(N, span, config.lateral_overlap_ratio, config.geometry)

    # Position strategy reordering
    if N > 1 and config.position_strategy == PositionStrategy.HEAVY_WAKE:
        mass_order = np.argsort(total_mass_per)
        factor_order = np.argsort(drag_factors)[::-1]
        slot_assignment = [0] * N
        for rank, aircraft_idx in enumerate(mass_order):
            slot_assignment[aircraft_idx] = factor_order[rank]
        reordered_weights = [0.0] * N
        reordered_hw_powers = [0.0] * N
        reordered_hw_masses = [0.0] * N
        for aircraft_idx in range(N):
            slot = slot_assignment[aircraft_idx]
            reordered_weights[slot] = weights[aircraft_idx]
            reordered_hw_powers[slot] = hw_powers[aircraft_idx]
            reordered_hw_masses[slot] = hw_masses[aircraft_idx]
        weights = reordered_weights
        hw_powers = reordered_hw_powers
        hw_masses = reordered_hw_masses
    elif N > 1 and config.position_strategy == PositionStrategy.HEAVY_FRONT:
        mass_order = np.argsort(total_mass_per)[::-1]
        weights = [weights[i] for i in mass_order]
        hw_powers = [hw_powers[i] for i in mass_order]
        hw_masses = [hw_masses[i] for i in mass_order]

    # Wing area — per aircraft, using AR if set
    wing_areas = [_wing_area_from_config(config, w, mission) for w in weights]
    total_wing_area = sum(wing_areas)

    # Aspect ratio (computed or from config)
    if config.aspect_ratio is not None:
        ar_each = config.aspect_ratio
    else:
        ar_each = span**2 / wing_areas[0] if wing_areas[0] > 0 else 0

    # Per-slot drag
    slot_induced_drags = []
    slot_parasite_drags = []
    for i in range(N):
        di = induced_drag(weights[i], span, mission, formation_factor=drag_factors[i])
        # Parasite drag uses actual wing area if AR is specified
        if config.aspect_ratio is not None:
            q = mission.dynamic_pressure()
            dp = q * wing_areas[i] * mission.cd0
        else:
            dp = parasite_drag(weights[i], mission)
        slot_induced_drags.append(di)
        slot_parasite_drags.append(dp)

    total_induced = sum(slot_induced_drags)
    total_parasite = sum(slot_parasite_drags)
    total_drag = total_induced + total_parasite

    # Station-keeping power
    sk_powers = []
    for i in range(N):
        is_leader = (i == 0 and N > 1) or N == 1
        sk = station_keeping_power(mission=mission, span_m=span, position_tolerance_m=2.0, is_leader=is_leader)
        sk_powers.append(sk)

    thrust_power = total_drag * mission.velocity
    total_hw_power = sum(hw_powers)
    total_sk_power = sum(sk_powers)
    total_payload_power = config.payload.power_W
    total_power = thrust_power + total_hw_power + total_sk_power + total_payload_power

    control_mass_total = sum(hw_masses)
    cost_score = mass_proxy_cost(structural_mass_kg=N * struct_mass_each, control_mass_kg=control_mass_total, N=N)
    b_eff = effective_span(N, span, config.lateral_overlap_ratio, config.geometry)

    # Energy balance — can the fleet sustain 24h flight?
    energy_result = compute_energy_balance(
        power_required_W=total_power,
        wing_area_m2=total_wing_area,
        coverage_fraction=panel_coverage,
        panel_efficiency=panel_efficiency,
        altitude_m=mission.altitude_m,
        latitude_deg=latitude_deg,
        day_of_year=day_of_year,
    )
    battery_mass = required_battery_mass(
        power_required_W=total_power,
        night_hours=energy_result.night_hours,
    )

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
        "wing_mass_each_kg": struct_mass_each,
        "wing_mass_total_kg": N * struct_mass_each,
        "control_mass_total_kg": control_mass_total,
        "payload_mass_kg": config.payload.mass_kg,
        "payload_power_W": config.payload.power_W,
        "battery_mass_kg": battery_mass,
        "total_mass_kg": total_fleet_mass,
        "total_mass_with_battery_kg": total_fleet_mass + battery_mass,
        "induced_drag_N": total_induced,
        "parasite_drag_N": total_parasite,
        "total_drag_N": total_drag,
        "thrust_power_W": thrust_power,
        "hw_power_W": total_hw_power,
        "sk_power_W": total_sk_power,
        "payload_power_total_W": total_payload_power,
        "total_power_W": total_power,
        "total_wing_area_m2": total_wing_area,
        "cost_score": cost_score,
        "energy_available_Wh": energy_result.energy_available_Wh,
        "energy_required_Wh": energy_result.energy_required_total_Wh,
        "energy_surplus_Wh": energy_result.surplus_Wh,
        "energy_closes": energy_result.closes,
        "day_hours": energy_result.day_hours,
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
