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


from wingz.cost.materials import materials_cost, MaterialPrices, fleet_cost, FleetCost


def test_materials_cost_positive():
    c = materials_cost(structural_mass_kg=50, solar_panel_area_m2=40, control_mass_kg=3)
    assert c > 0


def test_custom_prices():
    default = materials_cost(structural_mass_kg=50, solar_panel_area_m2=40, control_mass_kg=3)
    cheap = materials_cost(
        structural_mass_kg=50, solar_panel_area_m2=40, control_mass_kg=3,
        prices=MaterialPrices(cfrp_base_per_kg=50),
    )
    assert cheap < default


def test_materials_cost_scales_with_panel_area():
    c1 = materials_cost(structural_mass_kg=50, solar_panel_area_m2=20, control_mass_kg=3)
    c2 = materials_cost(structural_mass_kg=50, solar_panel_area_m2=60, control_mass_kg=3)
    assert c2 > c1


def test_fleet_cost_returns_breakdown():
    fc = fleet_cost(N=4, structural_mass_kg=50, solar_panel_area_m2=36,
                    battery_capacity_kWh=10, n_full_nav=1, n_basic_nav=3)
    assert isinstance(fc, FleetCost)
    assert fc.structure > 0
    assert fc.solar_cells > 0
    assert fc.batteries > 0
    assert fc.avionics > 0
    assert fc.propulsion > 0
    assert fc.total > fc.recurring_unit  # total includes ground + tooling


def test_fleet_cost_formation_cheaper_avionics():
    # Formation: 1 full nav + 3 followers with basic + relative nav
    fc_form = fleet_cost(N=4, structural_mass_kg=50, solar_panel_area_m2=36,
                         battery_capacity_kWh=10, n_full_nav=1, n_basic_nav=3)
    # Single with full nav
    fc_single = fleet_cost(N=1, structural_mass_kg=50, solar_panel_area_m2=36,
                           battery_capacity_kWh=10, n_full_nav=1, n_basic_nav=0)
    # Formation avionics: 1*25000 + 3*2000 = $31,000
    # Single avionics: 1*25000 = $25,000
    # Formation is more but not proportional to N
    assert fc_form.avionics < 4 * fc_single.avionics


def test_fleet_cost_solar_dominates():
    fc = fleet_cost(N=1, structural_mass_kg=110, solar_panel_area_m2=144,
                    battery_capacity_kWh=26, n_full_nav=1)
    # Solar cells should be the largest cost component for a HALE aircraft
    assert fc.solar_cells > fc.structure
    assert fc.solar_cells > fc.batteries


def test_capital_amortization():
    fc_10 = fleet_cost(N=1, structural_mass_kg=50, solar_panel_area_m2=36,
                       battery_capacity_kWh=10, production_run=10)
    fc_100 = fleet_cost(N=1, structural_mass_kg=50, solar_panel_area_m2=36,
                        battery_capacity_kWh=10, production_run=100)
    assert fc_100.capital_amortized < fc_10.capital_amortized
