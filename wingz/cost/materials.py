"""
Bottom-up materials cost model.
Estimates cost from component-level pricing.

Cost = C_cf*m + C_solar*A + C_avionics*m_ctrl + C_bat*E + C_asm*m

Default prices are order-of-magnitude estimates from market surveys:
- Carbon fiber: ~$120/kg (aerospace composite layup)
- Solar cells: ~$800/m^2 (Alta Devices / SunPower thin-film)
- Avionics: ~$5000/kg (tactical UAV component costs)
- Batteries: ~$300/kWh (2024 Li-ion cell-level)
- Assembly: ~$200/kg structure (rough aerospace labor)

See docs/formation_flight/references.md for discussion.
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
