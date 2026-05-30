from wingz.control.station_keeping import station_keeping_power
from wingz.mission.profiles import hale_20km, lower_altitude_le


def test_power_positive():
    p = station_keeping_power(mission=hale_20km(), span_m=20.0, position_tolerance_m=2.0)
    assert p > 0


def test_tighter_tolerance_more_power():
    p_loose = station_keeping_power(mission=hale_20km(), span_m=20.0, position_tolerance_m=5.0)
    p_tight = station_keeping_power(mission=hale_20km(), span_m=20.0, position_tolerance_m=1.0)
    assert p_tight > p_loose


def test_more_turbulence_more_power():
    p_calm = station_keeping_power(mission=hale_20km(), span_m=20.0, position_tolerance_m=2.0)
    p_rough = station_keeping_power(mission=lower_altitude_le(), span_m=20.0, position_tolerance_m=2.0)
    assert p_rough > p_calm


def test_leader_zero_station_keeping():
    p = station_keeping_power(mission=hale_20km(), span_m=20.0, position_tolerance_m=2.0, is_leader=True)
    assert p == 0.0
