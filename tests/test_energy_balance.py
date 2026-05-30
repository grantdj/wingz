import numpy as np
from wingz.solar.energy_balance import (
    EnergyBalanceResult,
    compute_energy_balance,
    required_battery_mass,
)


def test_energy_balance_returns_result():
    result = compute_energy_balance(
        power_required_W=200.0, wing_area_m2=50.0, coverage_fraction=0.8,
        panel_efficiency=0.25, altitude_m=20000, latitude_deg=30, day_of_year=172,
    )
    assert isinstance(result, EnergyBalanceResult)
    assert result.day_hours > 0
    assert result.night_hours > 0
    assert abs(result.day_hours + result.night_hours - 24.0) < 0.1


def test_generous_conditions_closes():
    result = compute_energy_balance(
        power_required_W=100.0, wing_area_m2=80.0, coverage_fraction=0.85,
        panel_efficiency=0.28, altitude_m=20000, latitude_deg=20, day_of_year=172,
    )
    assert result.closes


def test_impossible_conditions_fails():
    result = compute_energy_balance(
        power_required_W=500.0, wing_area_m2=10.0, coverage_fraction=0.7,
        panel_efficiency=0.20, altitude_m=20000, latitude_deg=55, day_of_year=355,
    )
    assert not result.closes


def test_battery_mass_positive():
    # 200W * 12h / 250 Wh/kg = 9.6 kg, targeting dawn_soc = 0.
    mass = required_battery_mass(power_required_W=200.0, night_hours=12.0, battery_energy_density_Wh_kg=250.0)
    assert mass > 0
    assert abs(mass - 9.6) < 0.1


def test_battery_mass_capacity_factor():
    mass = required_battery_mass(
        power_required_W=200.0,
        night_hours=12.0,
        battery_energy_density_Wh_kg=250.0,
        capacity_factor=1.3,
    )
    assert abs(mass - 12.48) < 0.1
