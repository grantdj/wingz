"""
Bottom-up materials cost model.

Covers recurring unit cost (materials + labor) and non-recurring costs
(tooling, development) amortized over a production run. Also includes
operational costs (GCS, launch/recovery, spares).

Prices are based on 2024-2026 aerospace market data:

Solar cells:
    III-V multi-junction ELO (MicroLink): $50-300/W depending on volume.
    At 38% efficiency and ~300 W/m² at altitude, that's $15,000-$90,000/m².
    We use $100/W as a mid-volume estimate ($30,000/m²).
    Source: MicroLink IARPA SOLSTICE presentation (2024), NREL III-V roadmap.

Carbon fiber composite:
    Finished CFRP parts (prepreg + autoclave + labor): $200-500/kg.
    We use $350/kg for aerospace-grade finished structure.
    Source: Aerospace composites market surveys.

Batteries:
    Aerospace-qualified Li-ion packs: $2,000-5,000/kWh (includes BMS, testing).
    We use $3,000/kWh for HALE-grade packs.
    Cell-level is $150-250/kWh but qualification adds 10-20x.
    Source: Aerospace battery market reports.

Avionics:
    Basic autopilot (Pixhawk + GPS): $500-2,000.
    Full HALE nav suite (redundant IMU, dual RTK, SATCOM): $5,000-50,000.
    We model as fixed cost per role, not per-kg.

Propulsion:
    Electric motor + ESC + propeller: $600-1,100 per combo (1-5 kW class).
    Source: T-Motor commercial pricing.

Ground infrastructure:
    GCS: $15,000-50,000 portable tactical.
    Launch/recovery: $50,000-200,000 for HALE.
    Shared across fleet.

Tooling/NRE:
    Wing mold: $50,000-200,000 per unique span.
    Formation advantage: all aircraft use same mold.

See docs/formation_flight/references.md for full citations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MaterialPrices:
    """Per-unit material and component pricing."""
    # Structure
    cfrp_finished_per_kg: float = 350.0        # $/kg, finished aerospace CFRP parts

    # Solar
    solar_cell_per_W: float = 100.0            # $/W, III-V ELO at mid-volume
    solar_W_per_m2: float = 300.0              # W/m² at altitude (38% eff * ~800 W/m² avg)

    # Batteries
    battery_pack_per_kWh: float = 3000.0       # $/kWh, aerospace-qualified pack

    # Avionics (fixed cost per unit, not per-kg)
    autopilot_basic: float = 1500.0            # basic flight computer + GPS
    autopilot_full_nav: float = 25000.0        # redundant IMU, dual RTK, SATCOM
    relative_nav_sensor: float = 500.0         # UWB/visual for follower

    # Propulsion
    propulsion_per_aircraft: float = 900.0     # motor + ESC + prop

    # Labor
    assembly_per_kg_structure: float = 300.0   # $/kg, integration & test labor

    # Ground infrastructure (shared across fleet)
    gcs_cost: float = 30000.0                  # portable tactical GCS
    launch_recovery: float = 100000.0          # HALE ground equipment

    # Tooling (per unique airframe design)
    wing_mold_tooling: float = 100000.0        # per unique span


@dataclass
class FleetCost:
    """Itemized cost breakdown for a fleet."""
    structure: float = 0.0
    solar_cells: float = 0.0
    batteries: float = 0.0
    avionics: float = 0.0
    propulsion: float = 0.0
    assembly: float = 0.0
    ground_infra: float = 0.0
    tooling_amortized: float = 0.0

    @property
    def recurring_unit(self) -> float:
        """Per-fleet recurring cost (materials + labor)."""
        return (self.structure + self.solar_cells + self.batteries
                + self.avionics + self.propulsion + self.assembly)

    @property
    def total(self) -> float:
        """Total including ground infra and amortized tooling."""
        return self.recurring_unit + self.ground_infra + self.tooling_amortized


def fleet_cost(
    N: int,
    structural_mass_kg: float,
    solar_panel_area_m2: float,
    battery_capacity_kWh: float,
    n_full_nav: int = 1,
    n_basic_nav: int = 0,
    production_run: int = 10,
    prices: Optional[MaterialPrices] = None,
) -> FleetCost:
    """
    Compute itemized cost for a fleet of N aircraft.

    n_full_nav: aircraft with full navigation suite (leader/sub-leader)
    n_basic_nav: aircraft with basic autopilot + relative nav (followers)
    If n_full_nav + n_basic_nav < N, remaining get basic autopilot only.
    production_run: number of fleets built (for tooling amortization)
    """
    p = prices or MaterialPrices()

    # Structure: total across fleet
    structure = p.cfrp_finished_per_kg * structural_mass_kg

    # Solar cells: priced per watt, convert from area
    solar_watts = solar_panel_area_m2 * p.solar_W_per_m2
    solar_cells = p.solar_cell_per_W * solar_watts

    # Batteries
    batteries = p.battery_pack_per_kWh * battery_capacity_kWh

    # Avionics: per aircraft by role
    n_basic_only = max(0, N - n_full_nav - n_basic_nav)
    avionics = (
        n_full_nav * p.autopilot_full_nav
        + n_basic_nav * (p.autopilot_basic + p.relative_nav_sensor)
        + n_basic_only * p.autopilot_basic
    )

    # Propulsion: per aircraft
    propulsion = N * p.propulsion_per_aircraft

    # Assembly labor
    assembly = p.assembly_per_kg_structure * structural_mass_kg

    # Ground infrastructure (one set per fleet, shared)
    ground_infra = p.gcs_cost + p.launch_recovery

    # Tooling: one mold per unique airframe, amortized over production run
    # Formation advantage: all N aircraft use the same mold
    tooling_amortized = p.wing_mold_tooling / production_run

    return FleetCost(
        structure=structure,
        solar_cells=solar_cells,
        batteries=batteries,
        avionics=avionics,
        propulsion=propulsion,
        assembly=assembly,
        ground_infra=ground_infra,
        tooling_amortized=tooling_amortized,
    )


# Keep the simple interface for backwards compatibility
def materials_cost(
    structural_mass_kg: float, solar_panel_area_m2: float, control_mass_kg: float,
    battery_capacity_kWh: float = 0.0, prices: Optional[MaterialPrices] = None,
) -> float:
    """Simple cost estimate (legacy interface). Use fleet_cost() for detailed breakdown."""
    p = prices or MaterialPrices()
    solar_watts = solar_panel_area_m2 * p.solar_W_per_m2
    return (
        p.cfrp_finished_per_kg * structural_mass_kg
        + p.solar_cell_per_W * solar_watts
        + p.autopilot_full_nav  # assume full nav for single aircraft
        + p.battery_pack_per_kWh * battery_capacity_kWh
        + p.assembly_per_kg_structure * structural_mass_kg
        + p.propulsion_per_aircraft
    )
