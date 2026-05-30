"""
Energy balance for 24-hour cycle closure.

For 30+ day endurance, the aircraft must generate enough solar energy during
the day to power flight AND charge batteries for the night.

References:
    Noth, A., "Design of Solar Powered Airplanes for Continuous Flight,"
        PhD Thesis, ETH Zurich, 2008. (Definitive treatment)
    Leutenegger, S. et al., "Solar Airplane Conceptual Design and Performance
        Estimation," J. Intelligent & Robotic Systems, Vol. 61, 2011.

See docs/formation_flight/references.md for full citations.
"""

from dataclasses import dataclass
from wingz.solar.power import (
    daily_energy_available, day_length_hours, solar_irradiance, panel_power,
)
import numpy as np


@dataclass
class EnergyBalanceResult:
    day_hours: float
    night_hours: float
    energy_available_Wh: float
    energy_required_day_Wh: float
    energy_required_night_Wh: float
    energy_required_total_Wh: float
    surplus_Wh: float
    closes: bool


def compute_energy_balance(
    power_required_W: float, wing_area_m2: float, coverage_fraction: float,
    panel_efficiency: float, altitude_m: float, latitude_deg: float, day_of_year: int,
) -> EnergyBalanceResult:
    day_hours = day_length_hours(latitude_deg, day_of_year)
    night_hours = 24.0 - day_hours
    energy_available = daily_energy_available(
        wing_area_m2, coverage_fraction, panel_efficiency, altitude_m, latitude_deg, day_of_year,
    )
    energy_required_day = power_required_W * day_hours
    energy_required_night = power_required_W * night_hours
    energy_required_total = energy_required_day + energy_required_night
    surplus = energy_available - energy_required_total
    return EnergyBalanceResult(
        day_hours=day_hours, night_hours=night_hours,
        energy_available_Wh=energy_available,
        energy_required_day_Wh=energy_required_day,
        energy_required_night_Wh=energy_required_night,
        energy_required_total_Wh=energy_required_total,
        surplus_Wh=surplus, closes=surplus >= 0,
    )


def required_coverage_fraction(
    energy_required_Wh: float,
    solar_margin: float,
    wing_area_m2: float,
    panel_efficiency: float,
    altitude_m: float,
    latitude_deg: float,
    day_of_year: int,
    max_coverage: float = 0.90,
) -> float:
    """
    Compute the panel coverage fraction needed to produce
    energy_required_Wh * solar_margin over one day.

    Returns the fraction of wing area that must be paneled (capped at max_coverage).
    If required coverage exceeds max_coverage, returns max_coverage — the caller
    should check whether the energy balance actually closes.
    """
    day_hours = day_length_hours(latitude_deg, day_of_year)
    peak_irr = solar_irradiance(altitude_m, latitude_deg, day_of_year)
    avg_irr = (2.0 / np.pi) * peak_irr

    # energy_available = wing_area * coverage * efficiency * avg_irr * day_hours
    # solve for coverage:
    energy_target = energy_required_Wh * solar_margin
    denominator = wing_area_m2 * panel_efficiency * avg_irr * day_hours
    if denominator <= 0:
        return max_coverage
    coverage = energy_target / denominator
    return min(coverage, max_coverage)


def required_battery_mass(
    power_required_W: float, night_hours: float,
    battery_energy_density_Wh_kg: float = 250.0,
    capacity_factor: float = 1.0,
) -> float:
    """
    m_bat = P * t_night * capacity_factor / energy_density.

    Nominal design target: dawn_soc = 0 after a full day/night cycle.
    Use capacity_factor values > 1 only for explicit installed-capacity
    derating such as usable fraction, charge losses, or end-of-life
    degradation.
    Ref: Noth (2008) Ch. 3.
    """
    return power_required_W * night_hours * capacity_factor / battery_energy_density_Wh_kg
