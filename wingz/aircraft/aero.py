"""
Component buildup aerodynamics for arbitrary aircraft configurations.

Computes CD0 from wetted areas of all components (wing, fuselage, boom,
tail surfaces, second wing, struts) and effective Oswald efficiency
considering multi-surface interference effects.

References:
    Raymer, Aircraft Design, Ch. 12 (drag buildup)
    Kroo, Aircraft Design: Synthesis and Analysis, Stanford (component drag)
    Prandtl, "Best Wing" / box wing theory (multi-surface efficiency)
"""

import numpy as np
from wingz.aircraft.geometry import AircraftGeometry


def skin_friction_coefficient(length_m: float, velocity: float, rho: float,
                               mu: float = 1.42e-5) -> float:
    """Turbulent flat plate Cf (Schlichting). mu default for 20km altitude."""
    Re = rho * velocity * length_m / mu
    Re = max(Re, 1e3)
    return 0.455 / (np.log10(Re) ** 2.58)


def wing_form_factor(t_c: float, sweep_rad: float) -> float:
    """Raymer wing form factor, calibrated to match solar HALE flight data.
    Noth (2008) and Zephyr/PHASA data suggest CD0_wing ~ 0.020 for t/c=0.14."""
    return (1 + 0.6 / 0.3 * t_c + 100 * t_c**4) * 1.1 * np.cos(sweep_rad)**0.28


def fuselage_form_factor(fineness: float) -> float:
    """Raymer fuselage form factor. fineness = length/diameter."""
    if fineness < 1:
        return 3.0
    return 1 + 60.0 / fineness**3 + fineness / 400.0


def compute_aero(geo: AircraftGeometry, velocity: float, rho: float,
                 t_c: float = 0.14) -> dict:
    """
    Full aerodynamic analysis for an arbitrary aircraft geometry.

    Returns dict with CD0, oswald_e, and component breakdown.
    """
    S_ref = geo.wing_area
    sweep_rad = np.radians(geo.sweep_deg)

    # ── Wing CD0 ──────────────────────────────────────────────────
    mac = geo.root_chord * 2/3 * (1 + geo.taper_ratio + geo.taper_ratio**2) / (
        1 + geo.taper_ratio)
    Cf_wing = skin_friction_coefficient(mac, velocity, rho)
    FF_wing = wing_form_factor(t_c, sweep_rad)
    S_wet_wing = 2.05 * S_ref  # upper + lower + LE
    CD0_wing = Cf_wing * FF_wing * S_wet_wing / S_ref

    # ── Fuselage CD0 ─────────────────────────────────────────────
    L_fuse = geo.fuselage_length
    D_fuse = geo.fuselage_diameter
    if D_fuse > 0.05 and L_fuse > 0.1:
        fineness = L_fuse / D_fuse
        S_wet_fuse = np.pi * D_fuse * L_fuse * 0.8  # tapered ends
        Cf_fuse = skin_friction_coefficient(L_fuse, velocity, rho)
        FF_fuse = fuselage_form_factor(fineness)
        CD0_fuse = Cf_fuse * FF_fuse * S_wet_fuse / S_ref
    else:
        CD0_fuse = 0.0
        S_wet_fuse = 0.0

    # ── Boom CD0 ─────────────────────────────────────────────────
    if geo.boom_length > 0.3:
        n_booms = 1
        S_wet_boom = np.pi * geo.boom_diameter * geo.boom_length * n_booms
        Cf_boom = skin_friction_coefficient(geo.boom_length, velocity, rho)
        CD0_boom = Cf_boom * 1.1 * S_wet_boom / S_ref  # FF ~1.1 for slender boom
    else:
        CD0_boom = 0.0
        S_wet_boom = 0.0

    # ── H-tail CD0 ───────────────────────────────────────────────
    S_htail = geo.h_tail_area
    if S_htail > 0.01:
        c_htail = np.sqrt(S_htail / geo.tail_aspect_ratio)
        Cf_htail = skin_friction_coefficient(c_htail, velocity, rho)
        FF_htail = wing_form_factor(0.10, 0.0)  # thin, unswept
        S_wet_htail = 2.05 * S_htail
        CD0_htail = Cf_htail * FF_htail * S_wet_htail / S_ref
    else:
        CD0_htail = 0.0
        S_wet_htail = 0.0

    # ── V-tail CD0 ───────────────────────────────────────────────
    S_vtail = geo.v_tail_area
    if S_vtail > 0.01:
        c_vtail = np.sqrt(S_vtail / (geo.tail_aspect_ratio * 0.6))
        Cf_vtail = skin_friction_coefficient(c_vtail, velocity, rho)
        FF_vtail = wing_form_factor(0.10, 0.0)
        S_wet_vtail = 2.05 * S_vtail
        CD0_vtail = Cf_vtail * FF_vtail * S_wet_vtail / S_ref
    else:
        CD0_vtail = 0.0
        S_wet_vtail = 0.0

    # ── Second wing CD0 ──────────────────────────────────────────
    S_wing2 = geo.wing2_area
    if S_wing2 > 0.01:
        ar2 = geo.wing2_span**2 / S_wing2 if S_wing2 > 0 else 8
        c_wing2 = np.sqrt(S_wing2 / ar2) if ar2 > 0 else 0.5
        Cf_wing2 = skin_friction_coefficient(c_wing2, velocity, rho)
        FF_wing2 = wing_form_factor(t_c, 0.0)
        S_wet_wing2 = 2.05 * S_wing2
        CD0_wing2 = Cf_wing2 * FF_wing2 * S_wet_wing2 / S_ref
    else:
        CD0_wing2 = 0.0
        S_wet_wing2 = 0.0

    # ── Strut CD0 ────────────────────────────────────────────────
    if geo.has_strut:
        strut_length = geo.half_span * geo.strut_span_frac * 1.2  # hypotenuse
        S_wet_strut = np.pi * geo.strut_diameter * strut_length * 2  # both sides
        Cf_strut = skin_friction_coefficient(strut_length, velocity, rho)
        CD0_strut = Cf_strut * 1.1 * S_wet_strut / S_ref
    else:
        CD0_strut = 0.0
        S_wet_strut = 0.0

    # ── Interference drag ────────────────────────────────────────
    n_junctions = 2  # wing-fuse
    if geo.has_tail:
        n_junctions += 3  # boom-fuse, boom-htail, vtail
    if geo.has_second_wing:
        n_junctions += 2
    if geo.has_strut:
        n_junctions += 2
    CD0_interference = 0.0003 * n_junctions  # clean HALE junctions

    # ── Miscellaneous drag ───────────────────────────────────────
    # Gaps, steps, antennas, pitot tubes, wiring bumps, panel edges
    CD0_misc = 0.002

    # ── Total CD0 ────────────────────────────────────────────────
    CD0 = (CD0_wing + CD0_fuse + CD0_boom + CD0_htail + CD0_vtail +
           CD0_wing2 + CD0_strut + CD0_interference + CD0_misc)

    # ── Oswald efficiency ────────────────────────────────────────
    # Noth (ETH, 2008) uses e = 0.85 for boom-tail solar HALE.
    # Clean flying wing can reach 0.88-0.90 but not higher — real planforms
    # have non-elliptic loading from taper, twist, and control surfaces.
    e_base = 0.88

    # Taper correction: 0.4-0.6 is near-optimal for elliptic loading
    taper_penalty = 0.04 * max(0, abs(geo.taper_ratio - 0.50) - 0.1)
    e_base -= taper_penalty

    # Fuselage interference: penalize wide fuselages relative to span
    fuse_penalty = 0.5 * geo.fuselage_diameter / geo.span
    e_base -= fuse_penalty

    # Tail surfaces create additional lift-dependent drag
    if geo.has_tail:
        tail_penalty = 0.02 * (geo.h_tail_area_frac + geo.v_tail_area_frac)
        e_base -= tail_penalty

    e_base = np.clip(e_base, 0.5, 0.95)

    # Box/joined wing bonus: Prandtl showed box wing can achieve e > 1
    # The ratio h/b (vertical gap / span) determines the benefit
    if geo.is_joined and geo.wing2_z_offset > 0.1:
        h_over_b = geo.wing2_z_offset / geo.span
        # Prandtl box wing: e_box ≈ 1 + 0.45 * h/b (for h/b < 0.3)
        e_box_factor = 1.0 + 0.45 * min(h_over_b, 0.3)
        e_base *= e_box_factor

    # Tandem/canard interference penalty (if not joined)
    if geo.has_second_wing and not geo.is_joined:
        # Downwash from forward wing degrades aft wing efficiency
        e_base *= 0.90

    # Strut-braced bonus: strut relieves root bending, allows thinner wing
    # which reduces profile drag (captured in CD0) but also slightly
    # improves span efficiency by constraining deflection
    if geo.has_strut:
        e_base *= 1.02

    e_base = np.clip(e_base, 0.4, 1.5)

    return {
        'CD0': CD0,
        'oswald_e': e_base,
        'CD0_wing': CD0_wing,
        'CD0_fuse': CD0_fuse,
        'CD0_boom': CD0_boom,
        'CD0_htail': CD0_htail,
        'CD0_vtail': CD0_vtail,
        'CD0_wing2': CD0_wing2,
        'CD0_strut': CD0_strut,
        'CD0_interference': CD0_interference,
        'S_wet_total': (S_wet_wing + S_wet_fuse + S_wet_boom + S_wet_htail +
                        S_wet_vtail + S_wet_wing2 + S_wet_strut),
    }
