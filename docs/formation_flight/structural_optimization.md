# Structural Optimization Engine

## Goal

Build a generative design tool that iterates on wing structure for
15–20m span solar HALE aircraft. The tool should explore the design
space autonomously and find the minimum-mass structure that meets all
constraints.

## Current Model vs Reality

### What we have (beam.py)

Single Euler-Bernoulli spar with two caps, a web at 30% of cap mass,
and a flat 0.3 kg/m² skin. Computes root bending moment from total
aircraft weight, sizes cap area from allowable stress. No taper, no
buckling, no ribs, no joints, no torsion.

### What a real 15–20m CFRP wing looks like

A typical small solar HALE wing at this scale:
- **Spar:** Round or D-section CFRP tube, possibly a single main spar
  at ~25-30% chord with a rear shear web at ~65% chord
- **Ribs:** Kevlar or foam ribs every 0.3–0.5m, carry distributed
  loads to spar
- **Skin:** Film covering (Mylar/Tedlar) on lower surface, solar cells
  bonded to upper surface acting as structural skin
- **Leading edge:** D-section CFRP fairing, carries torsion loads
- **Taper:** Chord tapers outboard (root chord > tip chord) to reduce
  outboard weight and match lift distribution
- **Construction:** Filament wound or prepreg CFRP tubes, wet-layup or
  prepreg ribs, vacuum-bagged or oven-cured

## Optimization Architecture

### Design Variables

```python
@dataclass
class WingDesign:
    # Spar geometry
    spar_type: str           # "round_tube", "d_section", "box"
    spar_location_pct: float # chordwise location (0.25-0.35 typical)
    n_spars: int             # 1 or 2
    rear_spar_pct: float     # if n_spars=2, rear spar location

    # Spar sizing (can vary along span via stations)
    spar_od_root: float      # outer diameter at root (m)
    spar_od_tip: float       # outer diameter at tip (m)
    spar_wall_root: float    # wall thickness at root (m)
    spar_wall_tip: float     # wall thickness at tip (m)

    # Ribs
    rib_spacing: float       # spacing along span (m)
    rib_thickness: float     # rib wall thickness (m)
    rib_material: str        # "cfrp", "kevlar", "foam_core"

    # Skin
    skin_type: str           # "film", "thin_cfrp", "solar_structural"
    skin_thickness: float    # if CFRP, thickness (m)
    skin_density: float      # areal density (kg/m²)

    # Planform
    taper_ratio: float       # tip_chord / root_chord (0.4-1.0)
    dihedral_break: bool     # mid-span dihedral break
    dihedral_angle: float    # degrees (0-10)
    dihedral_station: float  # span fraction where break occurs (0.4-0.6)

    # Wing segments (for transport/assembly)
    n_segments: int          # number of wing segments per side
    joint_mass_each: float   # mass per joint (kg)
```

### Load Cases

1. **1g cruise:** Elliptic lift distribution, weight distributed along
   span (batteries, panels, payload). Steady-state bending + torsion.
2. **Gust load (1.2g):** Stratospheric gust of 1–3 m/s. Adds
   incremental bending moment. For 15–20m span this is mild.
3. **Launch/recovery:** Hand launch or dolly launch — impulse load at
   root. Belly landing — distributed impact.
4. **Thermal cycling:** -70°C to +20°C daily. CTE mismatch between
   CFRP spar and Kevlar ribs or film skin creates thermal stresses.

### Constraints

```python
@dataclass
class StructuralConstraints:
    max_tip_deflection_pct: float = 15.0   # % of half-span under 1g
    min_buckling_margin: float = 1.5       # Euler buckling SF on spar
    min_torsional_stiffness: float = ...   # Nm²/rad, flutter avoidance
    max_skin_stress: float = ...           # Pa, skin panel buckling
    min_wall_thickness: float = 0.3e-3     # m, manufacturing minimum
    min_rib_spacing: float = 0.15          # m, practical minimum
    max_rib_spacing: float = 1.0           # m, skin panel span limit
```

### Objective

Minimize total wing mass:
```
m_total = m_spar + m_ribs + m_skin + m_joints + m_leading_edge
```

Subject to all constraints being satisfied under all load cases.

### Analysis Functions Needed

For each candidate design, compute:

1. **Section properties along span:**
   - I(y): moment of inertia vs spanwise station
   - J(y): torsional constant
   - A(y): cross-sectional area
   For round tube: I = π/64 × (OD⁴ - ID⁴), J = π/32 × (OD⁴ - ID⁴)

2. **Bending analysis:**
   - Distributed lift load (elliptic or specified)
   - Distributed weight (spar self-weight + panels + batteries)
   - Integrate shear and moment along span
   - Stress at each station: σ = M×c/I
   - Deflection by numerical integration of M/(EI)

3. **Buckling check:**
   - Euler column buckling of compression cap/wall
   - Local wall buckling (thin-walled tube): σ_cr = 0.3 × E × t/r
   - Skin panel buckling between ribs

4. **Torsion analysis:**
   - Aerodynamic pitching moment → torsion load
   - Torsional stiffness GJ along span
   - Twist angle at tip

5. **Mass rollup:**
   - Spar mass from wall thickness × circumference × length × density
   - Rib mass from rib geometry × count
   - Skin/covering mass from areal density × area
   - Joint mass × number of joints
   - Leading edge D-section mass

## Implementation Plan

### Phase 1: Parametric beam optimizer (build first)

Replace beam.py with a multi-station beam model:

```python
class TaperedTubeWing:
    """
    Wing with a round CFRP tube spar, tapered planform, and
    distributed mass. Computes mass, deflection, and stress
    at N stations along the span.
    """
    def analyze(self, design: WingDesign, loads: LoadCase) -> Results:
        # Discretize half-span into N stations
        # At each station: compute section properties from design
        # Integrate loads: shear(y), moment(y)
        # Compute stress, deflection, buckling margin
        # Sum mass from all components
        ...
```

Wrap in `scipy.optimize.differential_evolution` or similar global
optimizer. ~20 design variables, runs in seconds per evaluation,
can do 100K evaluations in minutes.

**What this gives us:**
- Optimal wall thickness distribution (taper schedule)
- Optimal rib spacing
- Whether 1 or 2 spars is better
- Whether dihedral breaks help at this scale
- Whether taper ratio matters
- Mass estimate within ~10-20% of reality

### Phase 2: Cross-section FEA (follow-on)

Use a 2D cross-section analysis tool to compute exact section
properties for non-circular sections (D-section, box beam). Feed into
the Phase 1 beam model.

Options:
- **PyNite** — lightweight Python beam FEA
- **sectionproperties** — Python package for arbitrary cross-sections
- **Custom** — straightforward for thin-walled sections

### Phase 3: Full aerostructural optimization (future)

Couple the structural model with the aero model for simultaneous
optimization of planform + structure:

- **OpenMDAO** — NASA's open-source MDO framework, designed for this
- **TACS** — Georgia Tech structural FEA, built for aerostructural opt
- **OpenAeroStruct** — MIT, specifically for wing aerostructural optimization

These tools can handle 3D topology optimization with composite layup
scheduling. This is where "a ton of compute" gets used — each FEA
evaluation takes minutes, and you need thousands of evaluations for
topology optimization.

## What We'd Learn

The key question for the business case: **how light can a 15–20m CFRP
wing actually be?**

Our current beam model says ~9–15 kg for the wing structure. Is that
conservative or optimistic? The optimizer would tell us:

- What's the theoretical minimum mass for a 20m span, AR 8, 50 kg
  MTOW wing that survives 1.2g gusts and 15% tip deflection?
- How sensitive is mass to span? (Is 15m substantially lighter than
  20m, or is there a plateau?)
- Does taper help enough to justify the manufacturing complexity?
- At what span does a dihedral break become necessary?
- Where should the batteries go (root vs distributed) for minimum
  structural mass?

## Quick Validation Check

Before building the optimizer, we can sanity-check our beam model
against known aircraft:

| Aircraft | Span | MTOW | Wing mass (est) | Our beam model |
|---|---|---|---|---|
| Zephyr S | 25m | 75 kg | ~7 kg (est) | ? |
| PHASA-35 | 35m | 150 kg | ~15 kg (est) | ? |

If our beam model is within 2× of the estimates, Phase 1 optimization
will give useful results. If it's off by 5×, we need to fix the
fundamentals first.
