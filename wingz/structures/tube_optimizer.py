"""
Parametric tube spar wing optimizer.

Models a tapered CFRP tube spar wing with ribs, skin, and optional
rear shear web. Discretizes the half-span into N stations and computes
bending stress, deflection, and buckling at each station.

Design variables (optimized):
    - Spar OD at root and tip (linear taper)
    - Spar wall thickness at root and tip (linear taper)
    - Rib spacing
    - Planform taper ratio (tip_chord / root_chord)

Fixed inputs:
    - Span, aspect ratio, total aircraft mass
    - Material properties (CFRP)
    - Load factor, airfoil t/c

The optimizer wraps this in scipy.optimize.differential_evolution
to find minimum-mass designs that satisfy all structural constraints.

Analysis includes:
    - Distributed lift (elliptic) and weight along span
    - Shear and bending moment at each station
    - Stress check: σ = M*c/I < σ_allowable
    - Euler buckling of tube wall: σ_cr = 0.3*E*t/r
    - Tip deflection by numerical integration of M/(EI)
    - Rib mass from rib count × rib geometry
    - Leading edge fairing mass estimate
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np
from scipy.optimize import differential_evolution

from wingz.constants import (
    CFRP_DENSITY, AIRFOIL_THICKNESS_RATIO, STRUCTURAL_LOAD_FACTOR,
    GRAVITY,
)


@dataclass
class TubeDesign:
    """Parameterized tube spar wing design."""
    # Spar geometry (linearly tapered from root to tip)
    spar_od_root: float       # outer diameter at root (m)
    spar_od_tip: float        # outer diameter at tip (m)
    spar_wall_root: float     # wall thickness at root (m)
    spar_wall_tip: float      # wall thickness at tip (m)

    # Ribs
    rib_spacing: float        # spacing along span (m)
    rib_thickness: float = 1.0e-3  # rib wall thickness (m)

    # Planform
    taper_ratio: float = 1.0  # tip_chord / root_chord (1.0 = rectangular)

    # Skin
    skin_areal_density: float = 0.20  # kg/m², film + ribs contribution


@dataclass
class WingRequirements:
    """Fixed requirements for the wing."""
    span_m: float
    aspect_ratio: float
    aircraft_mass_kg: float   # total per-aircraft mass (wing carries this)
    load_factor: float = STRUCTURAL_LOAD_FACTOR
    thickness_ratio: float = AIRFOIL_THICKNESS_RATIO

    # Material
    E: float = 135e9          # Pa, Young's modulus CFRP
    sigma_allow: float = 800e6  # Pa, allowable stress
    rho_material: float = CFRP_DENSITY  # kg/m³

    # Constraints
    max_tip_deflection_pct: float = 15.0  # % of half-span
    min_buckling_margin: float = 1.5

    # Distributed mass (fraction of aircraft mass on the wing)
    # Batteries, panels, payload distributed along span
    distributed_mass_fraction: float = 0.7  # 70% of mass is on the wing

    @property
    def root_chord(self) -> float:
        return self.span_m / self.aspect_ratio

    @property
    def half_span(self) -> float:
        return self.span_m / 2.0


@dataclass
class AnalysisResult:
    """Results from structural analysis of a wing design."""
    total_mass_kg: float
    spar_mass_kg: float
    rib_mass_kg: float
    skin_mass_kg: float
    le_mass_kg: float          # leading edge fairing

    max_stress_Pa: float
    max_stress_station: float  # spanwise location of max stress (fraction)
    stress_margin: float       # sigma_allow / max_stress - 1

    tip_deflection_m: float
    tip_deflection_pct: float

    min_buckling_margin: float
    buckling_station: float    # where buckling margin is worst

    feasible: bool             # all constraints satisfied
    n_ribs: int


def analyze_wing(design: TubeDesign, req: WingRequirements,
                 n_stations: int = 50) -> AnalysisResult:
    """
    Analyze a tube spar wing design at n_stations along the half-span.

    Returns mass breakdown, stress, deflection, and buckling margins.
    """
    L = req.half_span
    dy = L / n_stations
    y = np.linspace(0, L, n_stations + 1)  # station locations
    y_mid = (y[:-1] + y[1:]) / 2           # segment midpoints

    root_chord = req.root_chord

    # ── Section properties at each station ──────────────────────────
    # Linear taper of spar OD and wall thickness
    frac = y_mid / L  # 0 at root, 1 at tip
    od = design.spar_od_root + (design.spar_od_tip - design.spar_od_root) * frac
    wall = design.spar_wall_root + (design.spar_wall_tip - design.spar_wall_root) * frac
    id_ = od - 2 * wall
    id_ = np.maximum(id_, 0)

    # Tube section properties
    I = np.pi / 64 * (od**4 - id_**4)       # moment of inertia
    A_tube = np.pi / 4 * (od**2 - id_**2)   # cross-sectional area

    # Chord at each station (planform taper)
    chord = root_chord * (1.0 - (1.0 - design.taper_ratio) * frac)

    # Check: spar must fit inside airfoil
    max_spar_depth = chord * req.thickness_ratio
    spar_fits = od <= max_spar_depth

    # ── Load distribution ───────────────────────────────────────────
    W_total = req.aircraft_mass_kg * GRAVITY * req.load_factor

    # Lift: elliptic distribution (per half-span)
    # L(y) = L0 * sqrt(1 - (2y/b)^2), integrated = W/2
    eta = y_mid / L  # 0 to 1
    lift_shape = np.sqrt(np.maximum(1 - eta**2, 0))
    lift_shape /= np.sum(lift_shape * dy / L)  # normalize
    lift_dist = (W_total / 2) * lift_shape / L  # N/m

    # Distributed weight along span (spar self-weight + distributed components)
    # Spar weight per unit length
    spar_weight_dist = A_tube * req.rho_material * GRAVITY  # N/m

    # Distributed aircraft mass (batteries, panels, etc.)
    # Assume uniform distribution for now
    dist_mass = req.aircraft_mass_kg * req.distributed_mass_fraction
    dist_weight = (dist_mass * GRAVITY / 2) / L  # N/m per half-span, uniform

    # Net load = lift - weight (positive = upward bending)
    net_load = lift_dist - spar_weight_dist - dist_weight  # N/m

    # ── Integrate shear and moment from tip inward ──────────────────
    shear = np.zeros(n_stations)
    moment = np.zeros(n_stations)

    # Integrate from tip to root
    for i in range(n_stations - 2, -1, -1):
        shear[i] = shear[i + 1] + net_load[i + 1] * dy
        moment[i] = moment[i + 1] + shear[i + 1] * dy

    # ── Stress ──────────────────────────────────────────────────────
    c = od / 2  # distance to extreme fiber
    stress = np.zeros(n_stations)
    valid = I > 0
    stress[valid] = np.abs(moment[valid]) * c[valid] / I[valid]

    max_stress = np.max(stress) if np.any(valid) else float('inf')
    max_stress_idx = np.argmax(stress) if np.any(valid) else 0
    stress_margin = req.sigma_allow / max_stress - 1 if max_stress > 0 else float('inf')

    # ── Buckling ────────────────────────────────────────────────────
    # Thin-walled tube local buckling: σ_cr = 0.3 * E * t / r
    # (conservative; knockdown factor for imperfections included in 0.3)
    r = od / 2
    buckling_stress = np.zeros(n_stations)
    buckling_stress[r > 0] = 0.3 * req.E * wall[r > 0] / r[r > 0]

    buckling_margin = np.full(n_stations, float('inf'))
    stressed = stress > 0
    buckling_margin[stressed] = buckling_stress[stressed] / stress[stressed]

    min_buckling = np.min(buckling_margin)
    buckling_idx = np.argmin(buckling_margin)

    # ── Deflection ──────────────────────────────────────────────────
    # Integrate curvature κ = M/(EI) twice from root to tip
    curvature = np.zeros(n_stations)
    curvature[valid] = moment[valid] / (req.E * I[valid])

    # First integration: slope
    slope = np.zeros(n_stations)
    for i in range(1, n_stations):
        slope[i] = slope[i - 1] + curvature[i - 1] * dy

    # Second integration: deflection
    deflection = np.zeros(n_stations)
    for i in range(1, n_stations):
        deflection[i] = deflection[i - 1] + slope[i - 1] * dy

    tip_defl = deflection[-1]
    tip_defl_pct = tip_defl / L * 100

    # ── Mass rollup ─────────────────────────────────────────────────
    # Spar mass (both halves)
    spar_mass = 2 * np.sum(A_tube * dy) * req.rho_material

    # Rib mass
    n_ribs = max(2, int(np.ceil(req.span_m / design.rib_spacing)))
    # Each rib is roughly a thin plate filling the airfoil cross-section
    # Approximate as a rectangular frame: perimeter × thickness × height
    avg_chord = root_chord * (1 + design.taper_ratio) / 2
    avg_depth = avg_chord * req.thickness_ratio
    rib_perimeter = 2 * (avg_chord + avg_depth)  # rough
    rib_area = rib_perimeter * design.rib_thickness
    rib_mass_each = rib_area * avg_depth * 0.3 * req.rho_material  # 30% fill
    rib_mass = n_ribs * rib_mass_each

    # Skin mass
    wing_area = req.span_m * avg_chord  # approximate
    skin_mass = wing_area * design.skin_areal_density

    # Leading edge D-section fairing
    # ~15% of chord, thin CFRP shell, both halves
    le_chord_frac = 0.15
    le_thickness = 0.3e-3  # 0.3mm thin shell
    le_perimeter = np.pi * avg_chord * le_chord_frac  # D-section perimeter
    le_mass = 2 * L * le_perimeter * le_thickness * req.rho_material

    total_mass = spar_mass + rib_mass + skin_mass + le_mass

    # ── Feasibility ─────────────────────────────────────────────────
    feasible = (
        stress_margin >= 0
        and min_buckling >= req.min_buckling_margin
        and tip_defl_pct <= req.max_tip_deflection_pct
        and np.all(spar_fits)
        and np.all(wall > 0.3e-3)  # minimum gauge
        and np.all(id_ > 0)        # wall not thicker than radius
    )

    return AnalysisResult(
        total_mass_kg=total_mass,
        spar_mass_kg=spar_mass,
        rib_mass_kg=rib_mass,
        skin_mass_kg=skin_mass,
        le_mass_kg=le_mass,
        max_stress_Pa=max_stress,
        max_stress_station=y_mid[max_stress_idx] / L,
        stress_margin=stress_margin,
        tip_deflection_m=tip_defl,
        tip_deflection_pct=tip_defl_pct,
        min_buckling_margin=min_buckling,
        buckling_station=y_mid[buckling_idx] / L,
        feasible=feasible,
        n_ribs=n_ribs,
    )


def optimize_wing(
    req: WingRequirements,
    n_stations: int = 50,
    maxiter: int = 1000,
    popsize: int = 30,
    seed: int = 42,
    tol: float = 1e-6,
) -> tuple[TubeDesign, AnalysisResult]:
    """
    Find the minimum-mass tube spar wing for given requirements.

    Uses differential evolution (global optimizer) over design variables:
        [spar_od_root, spar_od_tip, spar_wall_root, spar_wall_tip,
         rib_spacing, taper_ratio, skin_areal_density]

    Returns (best_design, best_result).
    """
    max_depth = req.root_chord * req.thickness_ratio

    # Bounds: [lower, upper] for each design variable
    bounds = [
        (0.01, max_depth),          # spar_od_root
        (0.005, max_depth * 0.8),   # spar_od_tip
        (0.3e-3, 5e-3),            # spar_wall_root
        (0.3e-3, 3e-3),            # spar_wall_tip
        (0.15, 1.0),               # rib_spacing
        (0.4, 1.0),                # taper_ratio
        (0.10, 0.40),              # skin_areal_density
    ]

    infeasible_penalty = 1000.0  # kg

    def objective(x):
        design = TubeDesign(
            spar_od_root=x[0],
            spar_od_tip=x[1],
            spar_wall_root=x[2],
            spar_wall_tip=x[3],
            rib_spacing=x[4],
            taper_ratio=x[5],
            skin_areal_density=x[6],
        )
        result = analyze_wing(design, req, n_stations)

        if not result.feasible:
            # Penalize infeasible designs but still guide the optimizer
            penalty = infeasible_penalty
            if result.stress_margin < 0:
                penalty += abs(result.stress_margin) * 100
            if result.min_buckling_margin < req.min_buckling_margin:
                penalty += (req.min_buckling_margin - result.min_buckling_margin) * 100
            if result.tip_deflection_pct > req.max_tip_deflection_pct:
                penalty += (result.tip_deflection_pct - req.max_tip_deflection_pct) * 10
            return result.total_mass_kg + penalty

        return result.total_mass_kg

    result = differential_evolution(
        objective,
        bounds,
        maxiter=maxiter,
        popsize=popsize,
        seed=seed,
        tol=tol,
        polish=True,
    )

    best_design = TubeDesign(
        spar_od_root=result.x[0],
        spar_od_tip=result.x[1],
        spar_wall_root=result.x[2],
        spar_wall_tip=result.x[3],
        rib_spacing=result.x[4],
        taper_ratio=result.x[5],
        skin_areal_density=result.x[6],
    )
    best_result = analyze_wing(best_design, req, n_stations)

    return best_design, best_result
