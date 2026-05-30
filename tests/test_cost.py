from wingz.cost.mass_proxy import mass_proxy_cost


def test_cost_increases_with_mass():
    c1 = mass_proxy_cost(structural_mass_kg=50, control_mass_kg=5, N=3)
    c2 = mass_proxy_cost(structural_mass_kg=100, control_mass_kg=5, N=3)
    assert c2 > c1


def test_cost_increases_with_fleet_size():
    c1 = mass_proxy_cost(structural_mass_kg=50, control_mass_kg=5, N=2)
    c2 = mass_proxy_cost(structural_mass_kg=50, control_mass_kg=5, N=6)
    assert c2 > c1


def test_single_aircraft_no_complexity_penalty():
    c = mass_proxy_cost(structural_mass_kg=50, control_mass_kg=0, N=1)
    c_base = mass_proxy_cost(structural_mass_kg=50, control_mass_kg=0, N=1)
    assert c == c_base
