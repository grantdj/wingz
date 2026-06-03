"""
Monolithic aircraft configuration optimizer.

Single differential evolution run over ~28 continuous design variables.
Each evaluation runs the full energy-balance convergence loop (solar,
battery, structure, aero — all coupled). No predefined configuration
types — the optimizer discovers novel configurations.

The objective minimizes total aircraft mass (MTOW) subject to:
    - 24h energy closure (solar must charge battery for the night)
    - Structural feasibility (stress, buckling, deflection)
    - Spar fits inside airfoil
    - Fuselage fits payload bay
    - Minimum stability margins (if tail is present, volume coefficient check)

Usage:
    from wingz.aircraft.optimizer import optimize_aircraft, OptimizationConfig
    from wingz.aircraft.geometry import PayloadBay

    bay = PayloadBay(length_m=0.4, diameter_m=0.15, mass_kg=5.0, power_W=50.0)
    config = OptimizationConfig(payload=bay, latitude_deg=30.0)
    result = optimize_aircraft(config)
"""

from dataclasses import dataclass
from typing import Optional, Callable
import numpy as np
from scipy.optimize import differential_evolution

from wingz.aircraft.geometry import (
    AircraftGeometry, PayloadBay, enforce_payload_constraint,
    default_bounds, unpack, pack, DESIGN_VAR_NAMES, N_DESIGN_VARS,
)
from wingz.aircraft.aero import compute_aero
from wingz.aircraft.structures import aircraft_structural_mass
from wingz.solar.energy_balance import (
    compute_energy_balance, required_battery_mass, required_coverage_fraction,
)
from wingz.constants import (
    PANEL_EFFICIENCY, PANEL_AREAL_DENSITY, AIRFOIL_THICKNESS_RATIO,
    BATTERY_ENERGY_DENSITY, CL_MAX, GRAVITY, RHO_20KM, CFRP_DENSITY,
)


@dataclass
class OptimizationConfig:
    """Configuration for the aircraft optimizer."""
    payload: PayloadBay
    altitude_m: float = 20000
    rho: float = RHO_20KM
    latitude_deg: float = 30.0
    day_of_year: int = 172
    solar_margin: float = 3.0
    max_panel_coverage: float = 0.90
    panel_efficiency: float = PANEL_EFFICIENCY
    panel_areal_density: float = PANEL_AREAL_DENSITY
    propulsion_efficiency: float = 0.75
    stall_margin_day: float = 1.15
    stall_margin_night: float = 1.03
    battery_density: float = BATTERY_ENERGY_DENSITY
    t_c: float = AIRFOIL_THICKNESS_RATIO

    # Optimizer settings
    maxiter: int = 2000
    popsize: int = 40
    seed: int = 42
    tol: float = 1e-6
    convergence_iters: int = 40
    workers: int = -1  # -1 = all cores


@dataclass
class AircraftResult:
    """Complete result from aircraft optimization."""
    geometry: AircraftGeometry
    mtow_kg: float
    structural_mass_kg: float
    battery_mass_kg: float
    panel_mass_kg: float
    panel_coverage: float
    wing_area_m2: float
    solar_area_m2: float
    velocity_day: float
    velocity_night: float
    power_day_W: float
    power_night_W: float
    energy_closes: bool
    feasible: bool
    aero: dict
    structure: dict
    config_type: str  # human-readable description of what the optimizer found
    objective: float  # raw objective value


def classify_config(geo: AircraftGeometry) -> str:
    """Describe what the optimizer found in human terms."""
    parts = []

    if geo.has_second_wing:
        if geo.is_joined:
            if geo.wing2_z_offset > 0.3:
                parts.append("box-wing")
            else:
                parts.append("joined-wing")
        elif geo.wing2_x_offset < -0.5:
            parts.append("canard")
        elif geo.wing2_x_offset > 0.5:
            parts.append("tandem")
        else:
            parts.append("biplane")

    if geo.has_strut:
        parts.append("strut-braced")

    if not geo.has_tail:
        parts.append("flying-wing")
    elif geo.boom_length > 3.0:
        parts.append("long-boom")
    else:
        parts.append("boom-tail")

    if geo.fuselage_diameter < 0.10:
        parts.append("pod")
    elif geo.fuselage_length > 2.0:
        parts.append("fuselage")

    if geo.aspect_ratio > 18:
        parts.append(f"ultra-high-AR({geo.aspect_ratio:.0f})")
    elif geo.aspect_ratio > 12:
        parts.append(f"high-AR({geo.aspect_ratio:.0f})")

    if geo.taper_ratio < 0.5:
        parts.append("high-taper")

    return " / ".join(parts) if parts else "conventional"


def _evaluate_detailed(geo: AircraftGeometry, opt: 'OptimizationConfig') -> dict:
    """Run the same convergence loop as the objective but return all intermediate values."""
    from wingz.structures.beam import BeamStructure
    beam = BeamStructure()
    t_c = opt.t_c
    rho = opt.rho
    ar = geo.aspect_ratio
    wing_area = geo.wing_area
    solar_area = geo.solar_area

    structural_mass = beam.wing_mass(geo.span, ar, 20.0)
    non_wing = _non_wing_mass(geo)
    battery_mass = 2.0
    panel_mass = 0.0

    aero = {}
    P_day = P_night = v_day = v_night = panel_coverage = 0.0
    energy_result = None

    for _ in range(opt.convergence_iters):
        total_mass = structural_mass + non_wing + battery_mass + panel_mass + opt.payload.mass_kg + 0.4
        weight = total_mass * GRAVITY
        v_stall = np.sqrt(2 * weight / (rho * wing_area * CL_MAX))
        if not np.isfinite(v_stall) or v_stall <= 0:
            break
        v_day = opt.stall_margin_day * v_stall
        v_night = opt.stall_margin_night * v_stall

        aero = compute_aero(geo, v_day, rho, t_c)
        q_day = 0.5 * rho * v_day**2
        if q_day <= 0 or aero['oswald_e'] <= 0:
            break
        D_day = weight**2 / (q_day * np.pi * aero['oswald_e'] * geo.span**2) + q_day * wing_area * aero['CD0']
        q_night = 0.5 * rho * v_night**2
        D_night = weight**2 / (q_night * np.pi * aero['oswald_e'] * geo.span**2) + q_night * wing_area * aero['CD0']

        P_day = D_day * v_day / opt.propulsion_efficiency + 15.0 + 10.0 + opt.payload.power_W
        P_night = D_night * v_night / opt.propulsion_efficiency + 15.0 + 10.0 + opt.payload.power_W

        energy_24h = P_day * 13.9 + P_night * 10.1
        panel_coverage = required_coverage_fraction(
            energy_24h, opt.solar_margin, solar_area, opt.panel_efficiency,
            opt.altitude_m, opt.latitude_deg, opt.day_of_year, opt.max_panel_coverage)
        energy_result = compute_energy_balance(
            P_day, solar_area, panel_coverage, opt.panel_efficiency,
            opt.altitude_m, opt.latitude_deg, opt.day_of_year)

        nb = required_battery_mass(P_night, energy_result.night_hours, opt.battery_density)
        np_ = panel_coverage * solar_area * opt.panel_areal_density
        ns = beam.wing_mass(geo.span, ar, total_mass)

        if abs(nb - battery_mass) < 0.1 and abs(np_ - panel_mass) < 0.05 and abs(ns - structural_mass) < 0.1:
            break
        if nb > 1e4 or not np.isfinite(nb):
            break
        battery_mass = 0.6 * battery_mass + 0.4 * nb
        panel_mass = 0.6 * panel_mass + 0.4 * np_
        structural_mass = 0.6 * structural_mass + 0.4 * ns

    total_mass = structural_mass + non_wing + battery_mass + panel_mass + opt.payload.mass_kg + 0.4
    struct = aircraft_structural_mass(geo, total_mass, t_c)

    return {
        'total_mass': total_mass,
        'structural_mass': structural_mass + non_wing,
        'battery_mass': battery_mass,
        'panel_mass': panel_mass,
        'panel_coverage': panel_coverage,
        'v_day': v_day,
        'v_night': v_night,
        'P_day': P_day,
        'P_night': P_night,
        'energy_closes': energy_result.closes if energy_result else False,
        'feasible': struct['wing_feasible'] and (energy_result.closes if energy_result else False),
        'aero': aero,
        'struct': struct,
    }


def _non_wing_mass(geo: AircraftGeometry) -> float:
    """Non-wing structural mass: fuselage, boom, tail, motors, joints."""
    mass = 0.0
    # Fuselage
    fuse_wall = 0.5e-3
    mass += np.pi * geo.fuselage_diameter * geo.fuselage_length * fuse_wall * CFRP_DENSITY
    mass += 2 * np.pi * (geo.fuselage_diameter / 2)**2 * 1e-3 * CFRP_DENSITY
    # Boom
    if geo.has_tail:
        boom_wall = 0.5e-3
        boom_area = np.pi * (geo.boom_diameter**2 - (geo.boom_diameter - 2*boom_wall)**2) / 4
        mass += boom_area * geo.boom_length * CFRP_DENSITY
        mass += geo.h_tail_area * 1.5
        mass += geo.v_tail_area * 1.5
    # Second wing
    if geo.has_second_wing:
        mass += geo.wing2_area * (geo.skin_density + 0.5)
    # Struts
    if geo.has_strut:
        strut_length = geo.half_span * geo.strut_span_frac * 1.2
        strut_area = np.pi * (geo.strut_diameter**2 - (geo.strut_diameter - 1e-3)**2) / 4
        mass += 2 * strut_length * strut_area * CFRP_DENSITY
    # Motors + joints
    mass += max(1, round(geo.n_motors)) * 0.3 + 0.15
    return mass


def evaluate_aircraft(x: np.ndarray, opt: OptimizationConfig) -> float:
    """
    Objective function: evaluate a single aircraft configuration.

    Runs the full energy-balance convergence loop. Returns total mass (MTOW)
    with penalty for infeasible designs.
    """
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return _evaluate_aircraft_inner(x, opt)


def _evaluate_aircraft_inner(x: np.ndarray, opt: OptimizationConfig) -> float:
    geo = unpack(x)
    geo = enforce_payload_constraint(geo, opt.payload)

    t_c = opt.t_c
    rho = opt.rho

    # Quick geometric sanity checks
    max_spar_depth = geo.root_chord * t_c
    if geo.spar_od_root > max_spar_depth or geo.spar_od_tip > geo.tip_chord * t_c:
        return 5000.0
    if geo.wing_area <= 0 or geo.span <= 0:
        return 5000.0

    wing_area = geo.wing_area
    solar_area = geo.solar_area

    # Use the beam model for structural mass in the convergence loop
    # (same as sweep.py — it adapts to the actual loaded weight).
    # Then check the tube spar feasibility as a constraint at the end.
    from wingz.structures.beam import BeamStructure
    beam = BeamStructure()
    ar = geo.aspect_ratio

    structural_mass = beam.wing_mass(geo.span, ar, 20.0)
    battery_mass = 2.0
    panel_mass = 0.0

    # Add non-wing structural mass (fuselage, boom, tail, etc.)
    non_wing_struct = _non_wing_mass(geo)

    for iteration in range(opt.convergence_iters):
        total_mass = (structural_mass + non_wing_struct + battery_mass + panel_mass +
                      opt.payload.mass_kg + 0.4)

        weight = total_mass * GRAVITY
        v_stall = np.sqrt(2 * weight / (rho * wing_area * CL_MAX))
        if not np.isfinite(v_stall) or v_stall <= 0:
            return 5000.0

        v_day = opt.stall_margin_day * v_stall
        v_night = opt.stall_margin_night * v_stall

        aero = compute_aero(geo, v_day, rho, t_c)
        CD0 = aero['CD0']
        oswald_e = aero['oswald_e']

        q_day = 0.5 * rho * v_day**2
        if q_day <= 0 or oswald_e <= 0:
            return 5000.0
        D_induced = weight**2 / (q_day * np.pi * oswald_e * geo.span**2)
        D_parasite = q_day * wing_area * CD0
        D_total = D_induced + D_parasite
        if not np.isfinite(D_total) or D_total <= 0:
            return 5000.0

        q_night = 0.5 * rho * v_night**2
        if q_night <= 0:
            return 5000.0
        D_night = (weight**2 / (q_night * np.pi * oswald_e * geo.span**2) +
                   q_night * wing_area * CD0)
        if not np.isfinite(D_night):
            return 5000.0

        P_day = D_total * v_day / opt.propulsion_efficiency + 15.0 + 10.0 + opt.payload.power_W
        P_night = D_night * v_night / opt.propulsion_efficiency + 15.0 + 10.0 + opt.payload.power_W

        energy_24h = P_day * 13.9 + P_night * 10.1

        panel_coverage = required_coverage_fraction(
            energy_required_Wh=energy_24h,
            solar_margin=opt.solar_margin,
            wing_area_m2=solar_area,
            panel_efficiency=opt.panel_efficiency,
            altitude_m=opt.altitude_m,
            latitude_deg=opt.latitude_deg,
            day_of_year=opt.day_of_year,
            max_coverage=opt.max_panel_coverage,
        )

        energy_result = compute_energy_balance(
            power_required_W=P_day,
            wing_area_m2=solar_area,
            coverage_fraction=panel_coverage,
            panel_efficiency=opt.panel_efficiency,
            altitude_m=opt.altitude_m,
            latitude_deg=opt.latitude_deg,
            day_of_year=opt.day_of_year,
        )

        new_battery = required_battery_mass(
            power_required_W=P_night,
            night_hours=energy_result.night_hours,
            battery_energy_density_Wh_kg=opt.battery_density,
        )
        new_panel_mass = panel_coverage * solar_area * opt.panel_areal_density
        new_structural = beam.wing_mass(geo.span, ar, total_mass)

        batt_conv = abs(new_battery - battery_mass) < 0.1
        panel_conv = abs(new_panel_mass - panel_mass) < 0.05
        struct_conv = abs(new_structural - structural_mass) < 0.1

        if batt_conv and panel_conv and struct_conv:
            break

        if (new_battery > 1e4 or not np.isfinite(new_battery) or
            not np.isfinite(new_panel_mass) or not np.isfinite(new_structural) or
            new_structural > 1e4):
            return 5000.0

        battery_mass = 0.6 * battery_mass + 0.4 * new_battery
        panel_mass = 0.6 * panel_mass + 0.4 * new_panel_mass
        structural_mass = 0.6 * structural_mass + 0.4 * new_structural

    total_mass = (structural_mass + non_wing_struct + battery_mass + panel_mass +
                  opt.payload.mass_kg + 0.4)

    # Check tube spar feasibility at the converged total_mass
    struct_result = aircraft_structural_mass(geo, total_mass, t_c)

    # ── Penalties ────────────────────────────────────────────────
    penalty = 0.0

    # Energy must close
    if not energy_result.closes:
        deficit_frac = abs(energy_result.surplus_Wh) / max(energy_result.energy_required_total_Wh, 1)
        penalty += 500 + deficit_frac * 200

    # Structural feasibility
    if not struct_result['wing_feasible']:
        if struct_result['stress_margin'] < 0:
            penalty += abs(struct_result['stress_margin']) * 200
        if struct_result['min_buckling'] < 1.5:
            penalty += (1.5 - struct_result['min_buckling']) * 200
        if struct_result['tip_deflection_pct'] > 15.0:
            penalty += (struct_result['tip_deflection_pct'] - 15.0) * 20

    # Stability: if tail is present, check volume coefficient
    if geo.has_tail and geo.boom_length > 0.3:
        mac = geo.root_chord * 2/3 * (1 + geo.taper_ratio + geo.taper_ratio**2) / (
            1 + geo.taper_ratio)
        V_h = geo.h_tail_area * geo.boom_length / (wing_area * mac)
        if V_h < 0.3:
            penalty += (0.3 - V_h) * 100

    # Flying wing must have sweep for stability
    if not geo.has_tail and abs(geo.sweep_deg) < 5:
        penalty += (5 - abs(geo.sweep_deg)) * 20

    # Mass sanity
    if total_mass > 500 or total_mass < 2:
        penalty += 1000

    return total_mass + penalty


def _seed_population(bounds: list, opt: OptimizationConfig, popsize: int) -> np.ndarray:
    """
    Create an initial population seeded with known-good designs.

    Includes a conventional Zephyr-like config, a flying wing, and a
    high-AR boom-tail. The rest are random within bounds.
    """
    n_vars = len(bounds)
    rng = np.random.default_rng(opt.seed)

    # Known-good seed: Zephyr-like boom-tail, high AR
    seeds = []

    # Seed 1: conventional boom-tail, AR~12, 20m span
    s1 = AircraftGeometry(
        span=20.0, aspect_ratio=12.0, taper_ratio=0.6, sweep_deg=0.0,
        dihedral_deg=3.0, dihedral_break=0.5, dihedral_break_angle=5.0,
        fuselage_length=max(0.5, opt.payload.length_m * 1.1),
        fuselage_diameter=max(0.18, opt.payload.diameter_m * 1.1),
        boom_length=2.0, boom_diameter=0.03,
        h_tail_area_frac=0.08, v_tail_area_frac=0.04, tail_aspect_ratio=4.0,
        wing2_area_frac=0.0, wing2_x_offset=2.0, wing2_z_offset=0.0,
        wing2_span_frac=0.6, wing2_taper=0.7, wing2_join=0.0,
        strut_factor=0.0, strut_span_frac=0.5,
        spar_od_root=0.05, spar_od_tip=0.025,
        spar_wall_root=1.5e-3, spar_wall_tip=0.5e-3,
        rib_spacing=0.4, skin_density=0.20, n_motors=1.0, motor_span_frac=0.0,
    )
    seeds.append(pack(s1))

    # Seed 2: flying wing, higher AR, no tail
    s2 = AircraftGeometry(
        span=25.0, aspect_ratio=15.0, taper_ratio=0.5, sweep_deg=8.0,
        dihedral_deg=2.0, dihedral_break=0.5, dihedral_break_angle=3.0,
        fuselage_length=max(0.4, opt.payload.length_m * 1.1),
        fuselage_diameter=max(0.15, opt.payload.diameter_m * 1.1),
        boom_length=0.0, boom_diameter=0.02,
        h_tail_area_frac=0.0, v_tail_area_frac=0.0, tail_aspect_ratio=4.0,
        wing2_area_frac=0.0, wing2_x_offset=2.0, wing2_z_offset=0.0,
        wing2_span_frac=0.6, wing2_taper=0.7, wing2_join=0.0,
        strut_factor=0.0, strut_span_frac=0.5,
        spar_od_root=0.04, spar_od_tip=0.02,
        spar_wall_root=1.2e-3, spar_wall_tip=0.4e-3,
        rib_spacing=0.35, skin_density=0.18, n_motors=1.0, motor_span_frac=0.0,
    )
    seeds.append(pack(s2))

    # Seed 3: smaller, lighter, 15m span
    s3 = AircraftGeometry(
        span=15.0, aspect_ratio=10.0, taper_ratio=0.7, sweep_deg=0.0,
        dihedral_deg=2.0, dihedral_break=0.5, dihedral_break_angle=3.0,
        fuselage_length=max(0.5, opt.payload.length_m * 1.1),
        fuselage_diameter=max(0.18, opt.payload.diameter_m * 1.1),
        boom_length=1.5, boom_diameter=0.025,
        h_tail_area_frac=0.10, v_tail_area_frac=0.05, tail_aspect_ratio=4.0,
        wing2_area_frac=0.0, wing2_x_offset=2.0, wing2_z_offset=0.0,
        wing2_span_frac=0.6, wing2_taper=0.7, wing2_join=0.0,
        strut_factor=0.0, strut_span_frac=0.5,
        spar_od_root=0.06, spar_od_tip=0.03,
        spar_wall_root=1.5e-3, spar_wall_tip=0.5e-3,
        rib_spacing=0.4, skin_density=0.20, n_motors=1.0, motor_span_frac=0.0,
    )
    seeds.append(pack(s3))

    # Clip seeds to bounds
    lb = np.array([b[0] for b in bounds])
    ub = np.array([b[1] for b in bounds])
    for i in range(len(seeds)):
        seeds[i] = np.clip(seeds[i], lb, ub)

    # Fill rest with random
    total_pop = popsize * n_vars  # DE uses popsize × n_vars individuals... no
    # Actually DE popsize is multiplied by n_vars internally to get pop count
    # We need to provide init array of shape (popsize * n_vars, n_vars)? No.
    # init takes shape (M, N) where M >= popsize (actually DE popsize param is
    # the multiplier, total pop = popsize * N). We pass 'init' as array.
    total_individuals = popsize * n_vars  # This is what DE creates internally
    # Actually: the total pop is popsize (the parameter), which is a multiplier.
    # From scipy docs: "the total population size is popsize * len(x)"
    # But init should have shape (N, len(x)) where N = total pop size.
    n_pop = max(popsize * n_vars, len(seeds) + 10)

    pop = rng.uniform(lb, ub, size=(n_pop, n_vars))
    for i, seed in enumerate(seeds):
        pop[i] = seed

    return pop


def optimize_aircraft(opt: OptimizationConfig,
                      callback: Optional[Callable] = None) -> AircraftResult:
    """
    Run the monolithic aircraft optimizer.

    Uses differential evolution over all design variables simultaneously.
    Returns the best aircraft found.
    """
    bounds = default_bounds(opt.payload)
    init_pop = _seed_population(bounds, opt, opt.popsize)

    best_so_far = {'value': float('inf'), 'count': 0}

    def progress_callback(xk, convergence):
        best_so_far['count'] += 1
        val = evaluate_aircraft(xk, opt)
        if val < best_so_far['value']:
            best_so_far['value'] = val
            geo = unpack(xk)
            config_type = classify_config(geo)
            print(f"  Gen {best_so_far['count']:4d}: "
                  f"MTOW={val:.1f} kg, span={geo.span:.1f}m, AR={geo.aspect_ratio:.0f}, "
                  f"type={config_type}")
        if callback:
            callback(xk, convergence)

    print(f"Starting optimization: {N_DESIGN_VARS} design variables, "
          f"popsize={opt.popsize}, maxiter={opt.maxiter}")
    print(f"Payload: {opt.payload.mass_kg} kg, {opt.payload.power_W} W")
    print(f"Latitude: {opt.latitude_deg}°, altitude: {opt.altitude_m/1000:.0f} km")
    print()

    result = differential_evolution(
        evaluate_aircraft,
        bounds,
        args=(opt,),
        maxiter=opt.maxiter,
        init=init_pop,
        seed=opt.seed,
        tol=opt.tol,
        polish=True,
        callback=progress_callback,
        workers=opt.workers,
        updating='deferred' if opt.workers != 1 else 'immediate',
    )

    # Reconstruct the best result using the same convergence as the objective
    geo = unpack(result.x)
    geo = enforce_payload_constraint(geo, opt.payload)

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        detail = _evaluate_detailed(geo, opt)

    return AircraftResult(
        geometry=geo,
        mtow_kg=detail['total_mass'],
        structural_mass_kg=detail['structural_mass'],
        battery_mass_kg=detail['battery_mass'],
        panel_mass_kg=detail['panel_mass'],
        panel_coverage=detail['panel_coverage'],
        wing_area_m2=geo.wing_area,
        solar_area_m2=geo.solar_area,
        velocity_day=detail['v_day'],
        velocity_night=detail['v_night'],
        power_day_W=detail['P_day'],
        power_night_W=detail['P_night'],
        energy_closes=detail['energy_closes'],
        feasible=detail['feasible'],
        aero=detail['aero'],
        structure=detail['struct'],
        config_type=classify_config(geo),
        objective=result.fun,
    )


def sweep_seeds(opt: OptimizationConfig, n_seeds: int = 5) -> list[AircraftResult]:
    """
    Run optimization with multiple random seeds to explore different basins.

    Returns list of results sorted by MTOW.
    """
    results = []
    for i in range(n_seeds):
        print(f"\n{'='*60}")
        print(f"Seed {i+1}/{n_seeds}")
        print(f"{'='*60}")
        opt_i = OptimizationConfig(
            payload=opt.payload,
            altitude_m=opt.altitude_m,
            rho=opt.rho,
            latitude_deg=opt.latitude_deg,
            day_of_year=opt.day_of_year,
            solar_margin=opt.solar_margin,
            max_panel_coverage=opt.max_panel_coverage,
            panel_efficiency=opt.panel_efficiency,
            panel_areal_density=opt.panel_areal_density,
            propulsion_efficiency=opt.propulsion_efficiency,
            stall_margin_day=opt.stall_margin_day,
            stall_margin_night=opt.stall_margin_night,
            battery_density=opt.battery_density,
            t_c=opt.t_c,
            maxiter=opt.maxiter,
            popsize=opt.popsize,
            seed=opt.seed + i * 17,
            tol=opt.tol,
            convergence_iters=opt.convergence_iters,
            workers=opt.workers,
        )
        res = optimize_aircraft(opt_i)
        results.append(res)

    results.sort(key=lambda r: r.mtow_kg)
    return results
