"""
Energy balance for 24-hour cycle closure.
For 30+ day endurance, the aircraft must generate enough solar energy during
the day to power flight AND charge batteries for the night.
"""

from dataclasses import dataclass
from wingz.solar.power import daily_energy_available, day_length_hours


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


def required_battery_mass(
    power_required_W: float, night_hours: float, battery_energy_density_Wh_kg: float = 250.0,
) -> float:
    return power_required_W * night_hours / battery_energy_density_Wh_kg
