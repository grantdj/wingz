import numpy as np
from wingz.aerodynamics.formation_aero import (
    FormationGeometry,
    per_slot_drag_factor,
    effective_span,
)


def test_leader_gets_no_benefit():
    factors = per_slot_drag_factor(N=3, span_m=10.0, lateral_overlap_ratio=0.1, geometry=FormationGeometry.V)
    assert factors[0] == 1.0


def test_followers_get_benefit():
    factors = per_slot_drag_factor(N=3, span_m=10.0, lateral_overlap_ratio=0.1, geometry=FormationGeometry.V)
    for f in factors[1:]:
        assert f < 1.0


def test_more_overlap_more_benefit():
    factors_low = per_slot_drag_factor(N=3, span_m=10.0, lateral_overlap_ratio=0.0, geometry=FormationGeometry.V)
    factors_high = per_slot_drag_factor(N=3, span_m=10.0, lateral_overlap_ratio=0.1, geometry=FormationGeometry.V)
    assert factors_high[1] < factors_low[1]


def test_effective_span_greater_than_individual():
    b_eff = effective_span(N=3, span_m=10.0, lateral_overlap_ratio=0.1, geometry=FormationGeometry.V)
    assert b_eff > 10.0


def test_single_aircraft_effective_span_equals_span():
    b_eff = effective_span(N=1, span_m=20.0, lateral_overlap_ratio=0.0, geometry=FormationGeometry.V)
    assert abs(b_eff - 20.0) < 1e-10


def test_echelon_vs_v_formation():
    b_v = effective_span(N=5, span_m=10.0, lateral_overlap_ratio=0.1, geometry=FormationGeometry.V)
    b_ech = effective_span(N=5, span_m=10.0, lateral_overlap_ratio=0.1, geometry=FormationGeometry.ECHELON)
    assert b_v > b_ech


def test_v_formation_symmetric_slots():
    factors = per_slot_drag_factor(N=5, span_m=10.0, lateral_overlap_ratio=0.1, geometry=FormationGeometry.V)
    assert abs(factors[1] - factors[2]) < 1e-10
    assert abs(factors[3] - factors[4]) < 1e-10
