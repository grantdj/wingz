"""
Bottom-up materials cost model.
Estimates cost from component-level pricing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class MaterialPrices:
    carbon_fiber_per_kg: float = 120.0
    solar_cell_per_m2: float = 800.0
    avionics_per_kg: float = 5000.0
    battery_per_kWh: float = 300.0
    assembly_per_kg_structure: float = 200.0


def materials_cost(
    structural_mass_kg: float, solar_panel_area_m2: float, control_mass_kg: float,
    battery_capacity_kWh: float = 0.0, prices: Optional[MaterialPrices] = None,
) -> float:
    p = prices or MaterialPrices()
    return (
        p.carbon_fiber_per_kg * structural_mass_kg
        + p.solar_cell_per_m2 * solar_panel_area_m2
        + p.avionics_per_kg * control_mass_kg
        + p.battery_per_kWh * battery_capacity_kWh
        + p.assembly_per_kg_structure * structural_mass_kg
    )
