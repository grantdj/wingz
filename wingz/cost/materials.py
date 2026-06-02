"""
Bottom-up materials cost model.

Covers recurring unit cost (materials + labor), manufacturing capital
(autoclave, molds, factory), and operational infrastructure (GCS, launch).

Prices are based on 2024-2026 aerospace market data:

Solar cells:
    III-V multi-junction ELO (MicroLink): $50-300/W depending on volume.
    At 30% production efficiency and ~240 W/m² at altitude, that's
    $12,000-$72,000/m². We use $100/W mid-volume ($24,000/m²).
    Source: MicroLink IARPA SOLSTICE presentation (2024), NREL III-V roadmap.

Carbon fiber composite:
    Finished CFRP parts (prepreg + layup + cure + QA): $350/kg base at 10m span.
    Cost/kg scales with span — larger wings need bigger autoclaves, multi-section
    bonding, specialized handling, and transport. Exponent 0.8 per RAND R-4016.
    Source: RAND R-4016, aerospace composites cost literature.

Manufacturing capital:
    Autoclave: commercially available up to ~15m. Beyond that, custom build.
      - 10m: $2M (off-the-shelf industrial)
      - 15m: $5M (large commercial)
      - 20m+: custom, scales steeply (~span^2.5)
      - 60m: doesn't really exist; would be $50M+ custom facility
    Wing mold: $50K base at 10m, scales as span^1.5.
    Factory/cleanroom: scales with floor space needed for part handling.
    All amortized over production run. Throughput penalty for large parts:
    a single 60m autoclave cures one wing at a time; a factory with
    multiple 15m autoclaves can run in parallel.

Batteries:
    Aerospace-qualified Li-ion packs: $2,000-5,000/kWh (includes BMS, testing).
    We use $3,000/kWh for HALE-grade packs.
    Source: Aerospace battery market reports.

See docs/formation_flight/references.md for full citations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MaterialPrices:
    """Per-unit material and component pricing."""
    # Structure — base rate for small wings (~10m), scales with span
    cfrp_base_per_kg: float = 350.0            # $/kg, finished aerospace CFRP at ~10m span
    cfrp_span_ref_m: float = 10.0              # reference span for base rate
    cfrp_span_exponent: float = 0.8            # cost/kg scales as (span/ref)^exp
                                                # 0.8 per RAND R-4016, composite cost lit

    # Solar
    solar_cell_per_W: float = 100.0            # $/W, III-V ELO at mid-volume
    solar_W_per_m2: float = 240.0              # W/m² at altitude (30% eff * ~800 W/m² avg)

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

    # Manufacturing capital — amortized over production run
    # Autoclave: $2M base at 10m, scales steeply (custom builds above ~15m)
    autoclave_base: float = 2_000_000.0        # $ for a 10m-class autoclave
    autoclave_span_ref_m: float = 10.0
    autoclave_span_exponent: float = 2.5       # custom facility cost explodes with size

    # Wing mold
    wing_mold_base: float = 50_000.0           # $ for a 10m mold
    wing_mold_span_ref_m: float = 10.0
    wing_mold_span_exponent: float = 1.5

    # Factory/cleanroom floor space and handling equipment
    factory_base: float = 500_000.0            # $ for a 10m-class production cell
    factory_span_ref_m: float = 10.0
    factory_span_exponent: float = 1.5         # floor space + cranes + fixtures

    # Throughput: how many units/year one production line can produce.
    # Larger parts take longer to lay up, cure, and inspect.
    # A 15m line might do 50 wings/yr; a 60m line might do 5-10.
    # If production_run exceeds throughput, you need multiple lines.
    throughput_base_units_yr: float = 50.0     # units/yr at 10m span
    throughput_span_exponent: float = 1.0      # throughput drops as span grows
    production_years: float = 5.0              # years over which to amortize capital


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
    capital_amortized: float = 0.0    # autoclave + mold + factory, amortized

    @property
    def recurring_unit(self) -> float:
        """Per-fleet recurring cost (materials + labor)."""
        return (self.structure + self.solar_cells + self.batteries
                + self.avionics + self.propulsion + self.assembly)

    @property
    def total(self) -> float:
        """Total including ground infra and amortized capital."""
        return self.recurring_unit + self.ground_infra + self.capital_amortized


def fleet_cost(
    N: int,
    structural_mass_kg: float,
    solar_panel_area_m2: float,
    battery_capacity_kWh: float,
    span_m: float = 10.0,
    n_full_nav: int = 1,
    n_basic_nav: int = 0,
    production_run: int = 10,
    prices: Optional[MaterialPrices] = None,
) -> FleetCost:
    """
    Compute itemized cost for a fleet of N aircraft.

    span_m: wingspan of each aircraft (drives structure $/kg and capital costs)
    n_full_nav: aircraft with full navigation suite (leader/sub-leader)
    n_basic_nav: aircraft with basic autopilot + relative nav (followers)
    production_run: total number of fleets to build (for capital amortization)
    """
    p = prices or MaterialPrices()

    # Structure: $/kg increases with span
    span_factor = (span_m / p.cfrp_span_ref_m) ** p.cfrp_span_exponent
    cfrp_per_kg = p.cfrp_base_per_kg * span_factor
    structure = cfrp_per_kg * structural_mass_kg

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

    # Assembly labor: also scales with span complexity
    assembly = p.assembly_per_kg_structure * span_factor * structural_mass_kg

    # Ground infrastructure (one set per fleet, shared)
    ground_infra = p.gcs_cost + p.launch_recovery

    # Manufacturing capital: autoclave + mold + factory
    # All scale with span, amortized over production run.
    autoclave_factor = (span_m / p.autoclave_span_ref_m) ** p.autoclave_span_exponent
    autoclave_cost = p.autoclave_base * autoclave_factor

    mold_factor = (span_m / p.wing_mold_span_ref_m) ** p.wing_mold_span_exponent
    mold_cost = p.wing_mold_base * mold_factor

    factory_factor = (span_m / p.factory_span_ref_m) ** p.factory_span_exponent
    factory_cost = p.factory_base * factory_factor

    # Throughput: how many units one production line can produce per year.
    # If we need more than that, we need multiple lines (multiple autoclaves, etc.)
    throughput_factor = (span_m / p.autoclave_span_ref_m) ** p.throughput_span_exponent
    line_throughput_yr = p.throughput_base_units_yr / throughput_factor
    total_capacity = line_throughput_yr * p.production_years
    # Wings per fleet (each aircraft has one wing set)
    wings_needed = production_run * N
    n_lines = max(1.0, wings_needed / total_capacity)

    # Total capital = n_lines × (autoclave + factory) + mold (one mold shared)
    capital_total = n_lines * (autoclave_cost + factory_cost) + mold_cost
    capital_amortized = capital_total / production_run

    return FleetCost(
        structure=structure,
        solar_cells=solar_cells,
        batteries=batteries,
        avionics=avionics,
        propulsion=propulsion,
        assembly=assembly,
        ground_infra=ground_infra,
        capital_amortized=capital_amortized,
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
        p.cfrp_base_per_kg * structural_mass_kg  # no span scaling in legacy path
        + p.solar_cell_per_W * solar_watts
        + p.autopilot_full_nav  # assume full nav for single aircraft
        + p.battery_pack_per_kWh * battery_capacity_kWh
        + p.assembly_per_kg_structure * structural_mass_kg
        + p.propulsion_per_aircraft
    )
