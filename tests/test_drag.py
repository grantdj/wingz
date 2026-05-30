import numpy as np
from wingz.aerodynamics.drag import induced_drag, parasite_drag, total_drag
from wingz.mission.profiles import hale_20km


def test_induced_drag_decreases_with_span():
    m = hale_20km()
    d20 = induced_drag(1000.0, 20.0, m)
    d40 = induced_drag(1000.0, 40.0, m)
    d80 = induced_drag(1000.0, 80.0, m)
    assert d20 > d40 > d80


def test_induced_drag_inverse_square_span():
    m = hale_20km()
    d20 = induced_drag(1000.0, 20.0, m)
    d40 = induced_drag(1000.0, 40.0, m)
    ratio = d20 / d40
    assert abs(ratio - 4.0) < 0.01


def test_induced_drag_known_value():
    m = hale_20km()
    q = 0.5 * m.rho * m.velocity**2
    W = 1000.0
    b = 30.0
    expected = W**2 / (q * np.pi * m.oswald_e * b**2)
    assert abs(induced_drag(W, b, m) - expected) < 1e-6


def test_parasite_drag_proportional_to_area():
    m = hale_20km()
    d1 = parasite_drag(1000.0, m)
    d2 = parasite_drag(2000.0, m)
    assert abs(d2 / d1 - 2.0) < 0.01


def test_total_drag_is_sum():
    m = hale_20km()
    di = induced_drag(1000.0, 30.0, m)
    dp = parasite_drag(1000.0, m)
    dt = total_drag(1000.0, 30.0, m)
    assert abs(dt - (di + dp)) < 1e-10
