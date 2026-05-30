import numpy as np
from wingz.mission.profiles import MissionProfile, hale_20km, lower_altitude_le


def test_hale_profile_defaults():
    m = hale_20km()
    assert m.altitude_m == 20000
    assert 0.08 < m.rho < 0.10  # ~0.089 kg/m^3 at 20km
    assert 20 < m.velocity < 35
    assert m.min_endurance_days == 30


def test_lower_altitude_profile():
    m = lower_altitude_le()
    assert m.altitude_m < 20000
    assert m.rho > hale_20km().rho  # denser air
    assert m.velocity > hale_20km().velocity  # faster in denser air


def test_dynamic_pressure():
    m = hale_20km()
    q = m.dynamic_pressure()
    expected = 0.5 * m.rho * m.velocity**2
    assert abs(q - expected) < 1e-10


def test_wing_area():
    m = hale_20km()
    weight_N = 1000.0
    area = m.wing_area(weight_N)
    assert abs(area - weight_N / m.wing_loading_N_m2) < 1e-10
