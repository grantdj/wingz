
"""
formation_span_model.py

Starter tools for modeling the structural/aerodynamic trade between:
1) one large high-aspect-ratio wing
2) N smaller aircraft flying in formation

The goal is not to be "right" immediately, but to make the assumptions explicit
so you can sweep exponents, efficiencies, costs, and control penalties.
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class Mission:
    """Basic mission/aero assumptions."""
    total_weight_N: float = 1000.0        # total aircraft/fleet weight supported
    rho: float = 0.0889                   # kg/m^3, approx air density near 20 km
    velocity: float = 25.0                # m/s
    oswald_e: float = 0.85                # span efficiency factor
    cd0: float = 0.025                    # parasite drag coefficient
    wing_loading_N_m2: float = 45.0       # W/S


@dataclass
class StructureModel:
    """Span-scaling assumptions."""
    reference_span_m: float = 20.0
    reference_wing_mass_kg: float = 20.0
    span_exponent: float = 2.3            # m_wing ~ b^n
    material_cost_per_kg: float = 150.0
    manufacturing_exponent: float = 1.2   # cost ~ mass^p


@dataclass
class FormationModel:
    """Formation and control assumptions."""
    formation_induced_drag_factor: float = 0.75
    # 0.75 means formation reduces induced drag by 25% versus isolated aircraft.
    control_cost_per_aircraft: float = 1000.0
    coordination_cost_exponent: float = 1.2
    separation_penalty_drag_N: float = 0.0


def wing_area(weight_N: float, wing_loading_N_m2: float) -> float:
    return weight_N / wing_loading_N_m2


def aspect_ratio(span_m: float, area_m2: float) -> float:
    return span_m**2 / area_m2


def dynamic_pressure(rho: float, velocity: float) -> float:
    return 0.5 * rho * velocity**2


def lift_coefficient(weight_N: float, rho: float, velocity: float, area_m2: float) -> float:
    q = dynamic_pressure(rho, velocity)
    return weight_N / (q * area_m2)


def induced_drag(weight_N: float, span_m: float, mission: Mission, formation_factor: float = 1.0) -> float:
    """
    Induced drag from:
        C_Di = C_L^2 / (pi e AR)
        D_i = q S C_Di

    Algebraically this reduces to:
        D_i = W^2 / (q pi e b^2)

    so induced drag falls as 1 / span^2.
    """
    q = dynamic_pressure(mission.rho, mission.velocity)
    return formation_factor * weight_N**2 / (q * np.pi * mission.oswald_e * span_m**2)


def parasite_drag(weight_N: float, mission: Mission) -> float:
    area = wing_area(weight_N, mission.wing_loading_N_m2)
    q = dynamic_pressure(mission.rho, mission.velocity)
    return q * area * mission.cd0


def wing_mass(span_m: float, structure: StructureModel) -> float:
    return structure.reference_wing_mass_kg * (span_m / structure.reference_span_m) ** structure.span_exponent


def wing_cost(span_m: float, structure: StructureModel) -> float:
    mass = wing_mass(span_m, structure)
    return structure.material_cost_per_kg * mass ** structure.manufacturing_exponent


def single_aircraft(span_m: float, mission: Mission, structure: StructureModel) -> dict:
    weight = mission.total_weight_N
    area = wing_area(weight, mission.wing_loading_N_m2)
    return {
        "configuration": "single",
        "N": 1,
        "span_each_m": span_m,
        "total_span_m": span_m,
        "wing_area_each_m2": area,
        "AR_each": aspect_ratio(span_m, area),
        "induced_drag_N": induced_drag(weight, span_m, mission),
        "parasite_drag_N": parasite_drag(weight, mission),
        "total_drag_N": induced_drag(weight, span_m, mission) + parasite_drag(weight, mission),
        "wing_mass_kg": wing_mass(span_m, structure),
        "wing_cost": wing_cost(span_m, structure),
        "control_cost": 0.0,
        "total_cost": wing_cost(span_m, structure),
    }


def formation_aircraft(span_each_m: float, N: int, mission: Mission,
                       structure: StructureModel, formation: FormationModel) -> dict:
    weight_each = mission.total_weight_N / N
    area_each = wing_area(weight_each, mission.wing_loading_N_m2)

    di_each = induced_drag(
        weight_each,
        span_each_m,
        mission,
        formation_factor=formation.formation_induced_drag_factor
    )

    pd_each = parasite_drag(weight_each, mission)
    mass_each = wing_mass(span_each_m, structure)
    cost_each = wing_cost(span_each_m, structure)

    control_cost = formation.control_cost_per_aircraft * N ** formation.coordination_cost_exponent

    return {
        "configuration": "formation",
        "N": N,
        "span_each_m": span_each_m,
        "total_span_m": N * span_each_m,
        "wing_area_each_m2": area_each,
        "AR_each": aspect_ratio(span_each_m, area_each),
        "induced_drag_N": N * di_each,
        "parasite_drag_N": N * pd_each,
        "total_drag_N": N * (di_each + pd_each) + formation.separation_penalty_drag_N,
        "wing_mass_kg": N * mass_each,
        "wing_cost": N * cost_each,
        "control_cost": control_cost,
        "total_cost": N * cost_each + control_cost,
    }


def sweep_single(spans_m, mission=None, structure=None):
    mission = mission or Mission()
    structure = structure or StructureModel()
    return [single_aircraft(float(b), mission, structure) for b in spans_m]


def sweep_formation(spans_each_m, N_values, mission=None, structure=None, formation=None):
    mission = mission or Mission()
    structure = structure or StructureModel()
    formation = formation or FormationModel()

    rows = []
    for N in N_values:
        for b in spans_each_m:
            rows.append(formation_aircraft(float(b), int(N), mission, structure, formation))
    return rows


def pareto_filter(rows, x_key="total_cost", y_key="total_drag_N"):
    """
    Returns rows that are not dominated in both cost and drag.
    Lower is better for both x and y.
    """
    rows = sorted(rows, key=lambda r: (r[x_key], r[y_key]))
    pareto = []
    best_y = np.inf
    for row in rows:
        if row[y_key] < best_y:
            pareto.append(row)
            best_y = row[y_key]
    return pareto
