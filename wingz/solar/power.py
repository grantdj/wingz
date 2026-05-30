"""
Solar power model for high-altitude aircraft.
Models solar irradiance as a function of altitude, latitude, day-of-year, and panel characteristics.
"""

import numpy as np

SOLAR_CONSTANT = 1361.0


def solar_irradiance(altitude_m: float, latitude_deg: float, day_of_year: int) -> float:
    """Peak solar irradiance at given altitude. Uses exponential atmospheric transmission."""
    scale_height = 8500.0
    tau_sea_level = 0.3
    tau = tau_sea_level * np.exp(-altitude_m / scale_height)
    declination = _solar_declination(day_of_year)
    lat_rad = np.radians(latitude_deg)
    sin_elevation = np.sin(lat_rad) * np.sin(declination) + np.cos(lat_rad) * np.cos(declination)
    sin_elevation = np.clip(sin_elevation, 0.01, 1.0)
    airmass = 1.0 / sin_elevation
    return SOLAR_CONSTANT * np.exp(-tau * airmass)


def panel_power(wing_area_m2: float, coverage_fraction: float, panel_efficiency: float, irradiance_W_m2: float) -> float:
    return wing_area_m2 * coverage_fraction * panel_efficiency * irradiance_W_m2


def day_length_hours(latitude_deg: float, day_of_year: int) -> float:
    declination = _solar_declination(day_of_year)
    lat_rad = np.radians(latitude_deg)
    cos_hour_angle = -np.tan(lat_rad) * np.tan(declination)
    cos_hour_angle = np.clip(cos_hour_angle, -1.0, 1.0)
    hour_angle = np.arccos(cos_hour_angle)
    return float(2.0 * hour_angle * 12.0 / np.pi)


def daily_energy_available(
    wing_area_m2: float, coverage_fraction: float, panel_efficiency: float,
    altitude_m: float, latitude_deg: float, day_of_year: int,
) -> float:
    """Total energy from solar panels over one day (watt-hours)."""
    peak_irr = solar_irradiance(altitude_m, latitude_deg, day_of_year)
    day_hours = day_length_hours(latitude_deg, day_of_year)
    avg_irr = (2.0 / np.pi) * peak_irr
    avg_power = panel_power(wing_area_m2, coverage_fraction, panel_efficiency, avg_irr)
    return avg_power * day_hours


def _solar_declination(day_of_year: int) -> float:
    return np.radians(23.45) * np.sin(np.radians(360 / 365 * (day_of_year - 81)))
