import numpy as np
from wingz.solar.power import (
    solar_irradiance,
    panel_power,
    day_length_hours,
    daily_energy_available,
)


def test_irradiance_at_20km():
    irr = solar_irradiance(altitude_m=20000, latitude_deg=30, day_of_year=172)
    assert 1200 < irr < 1400


def test_irradiance_lower_altitude_less():
    irr_high = solar_irradiance(altitude_m=20000, latitude_deg=30, day_of_year=172)
    irr_low = solar_irradiance(altitude_m=12000, latitude_deg=30, day_of_year=172)
    assert irr_high > irr_low


def test_panel_power():
    p = panel_power(wing_area_m2=50.0, coverage_fraction=0.8, panel_efficiency=0.25, irradiance_W_m2=1300.0)
    expected = 50.0 * 0.8 * 0.25 * 1300.0
    assert abs(p - expected) < 1e-6


def test_day_length_equator_equinox():
    hours = day_length_hours(latitude_deg=0, day_of_year=80)
    assert abs(hours - 12.0) < 0.5


def test_day_length_summer_longer():
    summer = day_length_hours(latitude_deg=45, day_of_year=172)
    winter = day_length_hours(latitude_deg=45, day_of_year=355)
    assert summer > winter


def test_daily_energy():
    energy = daily_energy_available(
        wing_area_m2=50.0, coverage_fraction=0.8, panel_efficiency=0.25,
        altitude_m=20000, latitude_deg=30, day_of_year=172,
    )
    assert energy > 0
    assert energy < 200 * 3600
