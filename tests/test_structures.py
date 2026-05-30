import numpy as np
from wingz.structures.empirical import (
    EmpiricalStructure,
    SOLAR_HALE_DATA,
    fit_power_law,
)


def test_aircraft_data_exists():
    assert len(SOLAR_HALE_DATA) >= 7
    for entry in SOLAR_HALE_DATA:
        assert entry["span_m"] > 0
        assert entry["wing_mass_kg"] > 0
        assert "name" in entry


def test_fit_power_law():
    coefficient, exponent = fit_power_law(SOLAR_HALE_DATA)
    assert exponent > 1.5
    assert exponent < 4.0
    assert coefficient > 0


def test_wing_mass_increases_with_span():
    model = EmpiricalStructure.from_data(SOLAR_HALE_DATA)
    m20 = model.wing_mass(20.0)
    m40 = model.wing_mass(40.0)
    m60 = model.wing_mass(60.0)
    assert m20 < m40 < m60


def test_wing_mass_matches_data_order_of_magnitude():
    model = EmpiricalStructure.from_data(SOLAR_HALE_DATA)
    predicted = model.wing_mass(25.0)
    assert 2 < predicted < 30


def test_extrapolation_flag():
    model = EmpiricalStructure.from_data(SOLAR_HALE_DATA)
    result = model.wing_mass_with_confidence(25.0)
    assert result["interpolating"] is True
    result = model.wing_mass_with_confidence(5.0)
    assert result["interpolating"] is False
    result = model.wing_mass_with_confidence(100.0)
    assert result["interpolating"] is False


def test_ar_correction_increases_mass_at_high_ar():
    model = EmpiricalStructure.from_data(SOLAR_HALE_DATA)
    m_base = model.wing_mass(30.0)              # no AR → uses base
    m_ref = model.wing_mass(30.0, aspect_ratio=25.0)  # AR=ref → no correction
    m_high = model.wing_mass(30.0, aspect_ratio=40.0)  # AR>ref → heavier
    assert abs(m_base - m_ref) < 1e-6  # AR=ref same as no AR
    assert m_high > m_base


def test_ar_correction_decreases_mass_at_low_ar():
    model = EmpiricalStructure.from_data(SOLAR_HALE_DATA)
    m_base = model.wing_mass(30.0)
    m_low = model.wing_mass(30.0, aspect_ratio=15.0)   # AR<ref → lighter
    assert m_low < m_base


def test_ar_correction_monotonic():
    model = EmpiricalStructure.from_data(SOLAR_HALE_DATA)
    masses = [model.wing_mass(30.0, aspect_ratio=ar) for ar in [10, 15, 20, 25, 30, 35, 40]]
    for i in range(len(masses) - 1):
        assert masses[i] < masses[i + 1]
