import numpy as np
from wingz.mission.atmosphere import (
    standard_atmosphere,
    AtmosphereResult,
    mission_at_altitude,
)
from wingz.mission.profiles import MissionProfile


def test_sea_level():
    atm = standard_atmosphere(0)
    assert isinstance(atm, AtmosphereResult)
    assert abs(atm.rho - 1.225) < 0.01
    assert abs(atm.temperature_K - 288.15) < 1.0
    assert abs(atm.pressure_Pa - 101325) < 100


def test_20km():
    atm = standard_atmosphere(20000)
    assert 0.08 < atm.rho < 0.10  # ~0.089
    assert atm.temperature_K < 250  # stratosphere is cold


def test_density_decreases_with_altitude():
    rho_0 = standard_atmosphere(0).rho
    rho_10 = standard_atmosphere(10000).rho
    rho_20 = standard_atmosphere(20000).rho
    assert rho_0 > rho_10 > rho_20


def test_12km():
    atm = standard_atmosphere(12000)
    assert 0.28 < atm.rho < 0.35  # ~0.312


def test_turbulence_decreases_with_altitude():
    t_5 = standard_atmosphere(5000).turbulence_intensity
    t_15 = standard_atmosphere(15000).turbulence_intensity
    t_20 = standard_atmosphere(20000).turbulence_intensity
    assert t_5 > t_15 > t_20


def test_recommended_velocity():
    v_low = standard_atmosphere(5000).recommended_velocity
    v_high = standard_atmosphere(20000).recommended_velocity
    # Lower density needs higher speed OR lower wing loading
    # For solar HALE, velocity tends to be lower at altitude (low Re)
    assert v_low > 0
    assert v_high > 0


def test_mission_at_altitude():
    m = mission_at_altitude(20000)
    assert isinstance(m, MissionProfile)
    assert m.altitude_m == 20000
    assert 0.08 < m.rho < 0.10
    assert m.min_endurance_days == 30


def test_mission_at_different_altitudes():
    m12 = mission_at_altitude(12000)
    m20 = mission_at_altitude(20000)
    assert m12.rho > m20.rho
    assert m12.altitude_m == 12000
    assert m20.altitude_m == 20000
