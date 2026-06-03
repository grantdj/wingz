"""
Full-aircraft structural mass estimation.

Extends the tube spar wing model to include fuselage, tail booms,
empennage, second wing, struts, and joint penalties. Computes
feasibility from stress, buckling, and deflection constraints.
"""

import numpy as np
from wingz.aircraft.geometry import AircraftGeometry
from wingz.constants import (
    CFRP_DENSITY, AIRFOIL_THICKNESS_RATIO, STRUCTURAL_LOAD_FACTOR,
    GRAVITY,
)


def _tube_spar_analysis(half_span: float, root_chord: float, taper_ratio: float,
                         spar_od_root: float, spar_od_tip: float,
                         spar_wall_root: float, spar_wall_tip: float,
                         aircraft_mass_kg: float, distributed_mass_frac: float,
                         rib_spacing: float, skin_density: float,
                         t_c: float, load_factor: float,
                         E: float, sigma_allow: float, rho_mat: float,
                         strut_span_frac: float = 0.0,
                         n_stations: int = 50) -> dict:
    """
    Tube spar structural analysis for one wing pair.

    Returns mass breakdown and constraint margins. If strut_span_frac > 0,
    models a pin support at that span station (reduces root bending moment).
    """
    L = half_span
    dy = L / n_stations
    y = np.linspace(0, L, n_stations + 1)
    y_mid = (y[:-1] + y[1:]) / 2

    frac = y_mid / L
    od = spar_od_root + (spar_od_tip - spar_od_root) * frac
    wall = spar_wall_root + (spar_wall_tip - spar_wall_root) * frac
    id_ = np.maximum(od - 2 * wall, 0)

    I = np.pi / 64 * (od**4 - id_**4)
    A_tube = np.pi / 4 * (od**2 - id_**2)

    chord = root_chord * (1.0 - (1.0 - taper_ratio) * frac)
    max_spar_depth = chord * t_c
    spar_fits = od <= max_spar_depth

    # Loads
    W_total = aircraft_mass_kg * GRAVITY * load_factor

    eta = y_mid / L
    lift_shape = np.sqrt(np.maximum(1 - eta**2, 0))
    lift_shape /= np.sum(lift_shape * dy / L)
    lift_dist = (W_total / 2) * lift_shape / L

    spar_weight_dist = A_tube * rho_mat * GRAVITY
    dist_mass = aircraft_mass_kg * distributed_mass_frac
    dist_weight = (dist_mass * GRAVITY / 2) / L

    net_load = lift_dist - spar_weight_dist - dist_weight

    # Strut support: if present, add a reaction force at the strut station
    if strut_span_frac > 0.1:
        strut_idx = int(strut_span_frac * n_stations)
        strut_idx = min(strut_idx, n_stations - 1)
        # Approximate strut reaction: fraction of total load outboard of strut
        outboard_load = np.sum(net_load[strut_idx:]) * dy
        net_load[strut_idx] -= outboard_load / dy * 0.7  # strut carries ~70%

    # Shear and moment from tip inward
    shear = np.zeros(n_stations)
    moment = np.zeros(n_stations)
    for i in range(n_stations - 2, -1, -1):
        shear[i] = shear[i + 1] + net_load[i + 1] * dy
        moment[i] = moment[i + 1] + shear[i + 1] * dy

    c = od / 2
    stress = np.zeros(n_stations)
    valid = I > 0
    stress[valid] = np.abs(moment[valid]) * c[valid] / I[valid]

    max_stress = np.max(stress) if np.any(valid) else float('inf')
    stress_margin = sigma_allow / max_stress - 1 if max_stress > 0 else float('inf')

    r = od / 2
    buckling_stress = np.zeros(n_stations)
    buckling_stress[r > 0] = 0.3 * E * wall[r > 0] / r[r > 0]
    buckling_margin = np.full(n_stations, float('inf'))
    stressed = stress > 0
    buckling_margin[stressed] = buckling_stress[stressed] / stress[stressed]
    min_buckling = np.min(buckling_margin)

    curvature = np.zeros(n_stations)
    curvature[valid] = moment[valid] / (E * I[valid])
    slope = np.zeros(n_stations)
    deflection = np.zeros(n_stations)
    for i in range(1, n_stations):
        slope[i] = slope[i - 1] + curvature[i - 1] * dy
        deflection[i] = deflection[i - 1] + slope[i - 1] * dy

    tip_defl = deflection[-1]
    tip_defl_pct = tip_defl / L * 100

    # Mass rollup
    spar_mass = 2 * np.sum(A_tube * dy) * rho_mat

    n_ribs = max(2, int(np.ceil(2 * L / rib_spacing)))
    avg_chord = root_chord * (1 + taper_ratio) / 2
    avg_depth = avg_chord * t_c
    rib_perimeter = 2 * (avg_chord + avg_depth)
    rib_mass_each = rib_perimeter * 1.0e-3 * avg_depth * 0.3 * rho_mat
    rib_mass = n_ribs * rib_mass_each

    wing_area = 2 * L * avg_chord
    skin_mass = wing_area * skin_density

    le_thickness = 0.3e-3
    le_perimeter = np.pi * avg_chord * 0.15
    le_mass = 2 * L * le_perimeter * le_thickness * rho_mat

    total_mass = spar_mass + rib_mass + skin_mass + le_mass

    feasible = (
        stress_margin >= 0
        and min_buckling >= 1.5
        and tip_defl_pct <= 15.0
        and np.all(spar_fits)
        and np.all(wall > 0.3e-3)
        and np.all(id_ > 0)
    )

    return {
        'total_mass': total_mass,
        'spar_mass': spar_mass,
        'rib_mass': rib_mass,
        'skin_mass': skin_mass,
        'le_mass': le_mass,
        'stress_margin': stress_margin,
        'min_buckling': min_buckling,
        'tip_deflection_pct': tip_defl_pct,
        'tip_deflection_m': tip_defl,
        'feasible': feasible,
        'n_ribs': n_ribs,
    }


def aircraft_structural_mass(geo: AircraftGeometry, total_mass_kg: float,
                              t_c: float = AIRFOIL_THICKNESS_RATIO) -> dict:
    """
    Full aircraft structural mass estimation.

    Computes structural mass of all components:
    - Primary wing (tube spar analysis)
    - Fuselage
    - Tail boom + empennage
    - Second wing (if present)
    - Struts (if present)
    - Joints and misc

    Returns dict with mass breakdown and feasibility.
    """
    E = 135e9
    sigma_allow = 800e6
    rho_mat = CFRP_DENSITY
    load_factor = STRUCTURAL_LOAD_FACTOR

    # ── Primary wing ─────────────────────────────────────────────
    strut_frac = geo.strut_span_frac if geo.has_strut else 0.0

    wing_result = _tube_spar_analysis(
        half_span=geo.half_span,
        root_chord=geo.root_chord,
        taper_ratio=geo.taper_ratio,
        spar_od_root=geo.spar_od_root,
        spar_od_tip=geo.spar_od_tip,
        spar_wall_root=geo.spar_wall_root,
        spar_wall_tip=geo.spar_wall_tip,
        aircraft_mass_kg=total_mass_kg,
        distributed_mass_frac=0.7,
        rib_spacing=geo.rib_spacing,
        skin_density=geo.skin_density,
        t_c=t_c,
        load_factor=load_factor,
        E=E, sigma_allow=sigma_allow, rho_mat=rho_mat,
        strut_span_frac=strut_frac,
    )

    # ── Fuselage ─────────────────────────────────────────────────
    # Thin-walled CFRP cylinder with bulkheads
    fuse_wall = 0.5e-3  # 0.5mm wall
    fuse_skin_area = np.pi * geo.fuselage_diameter * geo.fuselage_length
    fuse_mass = fuse_skin_area * fuse_wall * rho_mat
    # Bulkheads (2 end caps)
    bulkhead_mass = 2 * np.pi * (geo.fuselage_diameter / 2)**2 * 1e-3 * rho_mat
    fuse_mass += bulkhead_mass

    # ── Tail boom ────────────────────────────────────────────────
    if geo.has_tail:
        boom_wall = 0.5e-3
        boom_area = np.pi * (geo.boom_diameter**2 - (geo.boom_diameter - 2*boom_wall)**2) / 4
        boom_mass = boom_area * geo.boom_length * rho_mat
    else:
        boom_mass = 0.0

    # ── Empennage ────────────────────────────────────────────────
    if geo.has_tail:
        # Simple mass estimate: tail surfaces at ~1.5 kg/m² (ribs + skin + spar)
        htail_mass = geo.h_tail_area * 1.5
        vtail_mass = geo.v_tail_area * 1.5
    else:
        htail_mass = 0.0
        vtail_mass = 0.0

    # ── Second wing ──────────────────────────────────────────────
    if geo.has_second_wing:
        wing2_span = geo.wing2_span
        wing2_area = geo.wing2_area
        wing2_root_chord = 2 * wing2_area / (wing2_span * (1 + geo.wing2_taper))
        # Lighter spar for secondary wing (carries less load)
        wing2_mass = wing2_area * (geo.skin_density + 0.5)  # skin + light spar
    else:
        wing2_mass = 0.0

    # ── Struts ───────────────────────────────────────────────────
    if geo.has_strut:
        strut_length = geo.half_span * geo.strut_span_frac * 1.2
        strut_area = np.pi * (geo.strut_diameter**2 - (geo.strut_diameter - 1e-3)**2) / 4
        strut_mass = 2 * strut_length * strut_area * rho_mat  # both sides
    else:
        strut_mass = 0.0

    # ── Joints ───────────────────────────────────────────────────
    joint_mass = 0.1  # wing-fuse
    if geo.has_tail:
        joint_mass += 0.05  # boom joint
    if geo.has_second_wing:
        joint_mass += 0.1
        if geo.is_joined:
            joint_mass += 0.2  # tip joints for box wing
    if geo.has_strut:
        joint_mass += 0.1

    # ── Motor mass ───────────────────────────────────────────────
    # Scale with power needed (rough: 0.5 kg per motor for this class)
    n_motors = max(1, round(geo.n_motors))
    motor_mass = n_motors * 0.3

    # ── Total ────────────────────────────────────────────────────
    structural_mass = (wing_result['total_mass'] + fuse_mass + boom_mass +
                       htail_mass + vtail_mass + wing2_mass + strut_mass +
                       joint_mass + motor_mass)

    return {
        'structural_mass': structural_mass,
        'wing_mass': wing_result['total_mass'],
        'wing_spar_mass': wing_result['spar_mass'],
        'wing_rib_mass': wing_result['rib_mass'],
        'wing_skin_mass': wing_result['skin_mass'],
        'wing_le_mass': wing_result['le_mass'],
        'fuse_mass': fuse_mass,
        'boom_mass': boom_mass,
        'htail_mass': htail_mass,
        'vtail_mass': vtail_mass,
        'wing2_mass': wing2_mass,
        'strut_mass': strut_mass,
        'joint_mass': joint_mass,
        'motor_mass': motor_mass,
        'stress_margin': wing_result['stress_margin'],
        'min_buckling': wing_result['min_buckling'],
        'tip_deflection_pct': wing_result['tip_deflection_pct'],
        'tip_deflection_m': wing_result['tip_deflection_m'],
        'wing_feasible': wing_result['feasible'],
        'n_ribs': wing_result['n_ribs'],
    }
