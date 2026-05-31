# Formation Flight Modeling — Design Spec

> **Implementation status (updated 2026-05-29):** The following features from this
> spec have been implemented:
> - **Atmosphere model** (`wingz/mission/atmosphere.py`) — ISA standard atmosphere
>   covering troposphere and lower stratosphere (0–20 km); enables altitude as a
>   sweep parameter.
> - **Payload model** (`wingz/mission/payload.py`) — payload mass and power draw
>   as explicit design inputs; payload capacity surfaced as an output metric.
> - **Energy balance integration** — the sweep engine now uses 24h energy cycle
>   closure as a feasibility gate; designs that fail closure are excluded from
>   downstream analysis.
> - **Aspect ratio as independent parameter** — AR can be swept independently of
>   span, decoupling structural and aerodynamic tradeoffs in the sweep engine.

## Overview

This project investigates whether a fleet of smaller autonomous solar-powered aircraft
flying in coordinated formation can achieve the aerodynamic performance of a much larger
high-aspect-ratio aircraft while avoiding the structural penalties of extreme wingspans.

**Core thesis:** Structural complexity scales faster than aerodynamic benefit as span
increases. Formation flight trades structural complexity for control complexity — and
autonomous control systems may be cheaper than large-scale aerospace structures.

**Mission class:** Solar-powered, long-endurance (30+ day), at two altitude regimes:
1. HALE (~20 km) — stratospheric, very low air density
2. Lower-altitude long-endurance — denser air, different structural/solar tradeoffs

## Goals

1. **Validate the thesis quantitatively** — build progressively more realistic sub-models
   (calibrated empirical scaling, spacing-dependent formation aero, real control hardware
   mass/power) to get numbers trustworthy enough to draw conclusions from.
2. **Build an interactive exploration tool** — parametric models with many sweepable knobs,
   good visualization, and sensitivity analysis for rapid "what if" exploration.

## Architecture

Layered physics library with separate modules per domain, composed through a top-level
evaluator. Each sub-model is independently testable and swappable.

```
docs/
  formation_flight/         # expanded writeups
  future_ideas.md           # tethering, speculative concepts
wingz/                      # importable Python package
  __init__.py
  structures/
    __init__.py
    empirical.py            # power-law scaling calibrated to real aircraft
    beam.py                 # (future) analytical Euler-Bernoulli spar model
  aerodynamics/
    __init__.py
    drag.py                 # induced + parasite drag
    formation_aero.py       # spacing-dependent wake model → effective span
  solar/
    __init__.py
    power.py                # solar flux vs altitude/latitude/season
    energy_balance.py       # power required vs available, battery sizing, 24h cycle
  control/
    __init__.py
    architectures.py        # leader/follower, tiered, mesh — mass/power profiles
    station_keeping.py      # energy cost of formation maintenance
  cost/
    __init__.py
    mass_proxy.py           # cost as f(structural mass, control mass, complexity)
    materials.py            # bottom-up: carbon fiber $/kg, solar $/W, avionics pricing
  mission/
    __init__.py
    profiles.py             # mission definitions (HALE 20km, lower-altitude LE)
    endurance.py            # 24h energy cycle closure check
    atmosphere.py           # ISA standard atmosphere (0-20 km)
    payload.py              # payload mass/power definitions
  evaluation/
    __init__.py
    sweep.py                # parameter sweep engine
    pareto.py               # multi-objective Pareto analysis
  visualization/
    __init__.py
    plots.py                # matplotlib plotting functions
scripts/
  sweep_single_vs_formation.py
  sensitivity_analysis.py
notebooks/                  # optional Jupyter exploration
```

## Module Details

### 1. Structures (`wingz/structures/`)

#### `empirical.py` — Calibrated Power-Law Scaling

Fit `m_wing = a * b^n` against real solar/HALE aircraft data:

| Aircraft | Span (m) | Wing mass (kg) | MTOW (kg) | Source | Mass confidence |
|----------|----------|-----------------|-----------|--------|-----------------|
| Zephyr S | 25 | ~7 | 75 | Airbus | Estimated |
| PHASA-35 | 35 | ~15 | 150 | BAE Systems | Estimated |
| Pathfinder Plus | 36.3 | ~30 | 315 | NASA | Estimated |
| Odysseus | 74 | ~130 | 180 | Boeing Aurora | Estimated |
| Helios | 75.3 | ~180 | 1052 | NASA | Estimated |
| HAPSMobile Sunglider | 78 | ~200 | 260 | SoftBank | Estimated |
| Solar Impulse 2 | 71.9 | ~250 | 2300 | SI Foundation | Estimated |

Most wing masses are estimates derived from published MTOW and typical structural
fractions. The fit will track which values are confirmed vs. estimated.

Interface: `span_m → (mass_kg, cost, deflection)` — same interface the future beam
model will implement.

The model returns a confidence flag for whether the query point is within the
interpolation range or extrapolating.

#### `beam.py` — Future Analytical Model

Euler-Bernoulli cantilever beam with real material properties (carbon fiber layup).
Solves for required spar cap area to meet deflection and stress limits at each span.
Captures the cube-law deflection physics directly. Will be built once empirical
results identify promising regions of the design space.

### 2. Aerodynamics (`wingz/aerodynamics/`)

#### `drag.py` — Basic Drag Model

- Induced drag: `D_i = W² / (q π e b²)` — falls as 1/span²
- Parasite drag: `D_p = q S C_D0`
- Total drag: sum of induced + parasite

#### `formation_aero.py` — Formation Aerodynamics

**Physics layer** (Hummel/Lissaman classical results):

Induced drag reduction for a trailing aircraft depends on:
- **Lateral overlap ratio** (tip-to-tip gap / span) — optimal at ~10% span overlap
- **Streamwise separation** — vortex wake rolls up and descends; too far back misses upwash
- **Position in formation** — leader gets no benefit, first follower gets the most,
  subsequent followers see diminishing returns that asymptote

The drag reduction is not uniform across aircraft. This asymmetry is what makes the
position assignment strategy meaningful.

In a V formation, the two slots immediately behind the leader (left and right) are
**not necessarily symmetric** in benefit. In still air with identical aircraft they
are equivalent by symmetry. However, crosswind, asymmetric vortex rollup, or
heterogeneous aircraft (different spans/weights on each side) break this symmetry.
The model must compute drag reduction per-aircraft, per-slot, not assume uniform
benefit across symmetric positions.

**Interface layer:**

Expose the physics as an **effective span** for the whole formation:
`b_eff = f(N, spacing, geometry)` which plugs into the standard induced drag equation.

Formation geometries: echelon, V, inline.

### 3. Solar Power (`wingz/solar/`)

#### `power.py` — Solar Flux Model

- Solar irradiance vs. altitude — ~1361 W/m² at 20 km (above most atmosphere)
- Latitude and season — day length and solar elevation angle drive available energy
- Panel efficiency — 38% for MicroLink III-V ELO cells (flight-proven on Zephyr/PHASA-35)
- Panel coverage fraction — upper wing surface minus control surfaces, spar caps, etc.

#### `energy_balance.py` — Endurance Gate

The 30-day requirement means the aircraft must close the energy balance every 24-hour
cycle, including worst-case day (winter solstice at mission latitude).

- Power required = (total drag × velocity) + avionics + control hardware + payload
- Power available = solar panel output × time-of-day profile
- Night survival = battery energy must cover power required through darkness
- **Battery mass feedback loop** — more battery → more weight → more drag → more power
  required → more battery. This is the critical sizing loop for solar HALE.

For heterogeneous formations, the energy balance is per-aircraft: the leader (light,
up front) has a different power budget than the heavy follower in the wake.

### 4. Control (`wingz/control/`)

#### `architectures.py` — Formation Architectures

Three architectures, each a sweepable configuration:

| Architecture | Leader | Followers | Approx nav mass |
|---|---|---|---|
| **Leader/follower** | Full IMU + GPS + comms | Relative nav (UWB/visual) + datalink | Leader: ~2-3 kg, Follower: ~0.3-0.5 kg |
| **Tiered** | Full nav | Sub-leaders: partial, Followers: relative | Graduated |
| **Mesh** | All carry partial suite | Cooperative localization | ~1 kg each |

Each architecture defines a resilience model — what happens when an aircraft is lost.

#### `station_keeping.py` — Station-Keeping Energy

- Additional thrust for continuous position corrections
- Scales with turbulence intensity (calmer at 20 km)
- Scales with required position tolerance (tighter = more benefit but more effort)
- Vortex wake itself adds turbulence for the follower

### 5. Position Assignment Strategy

A key design insight: the formation "leader" (front position, clean air) should be the
**lightest** aircraft with the best power-to-weight ratio. The **heaviest** aircraft
(full nav/comms stack) should sit in the **best wake position** (first follower slot)
where induced drag reduction is greatest.

This is a natural synergy — the aircraft that needs the most aerodynamic help is the
one with the best sensors for precise station-keeping, and it's in the position where
station-keeping precision matters most.

Three sweepable strategies:
- `heavy_front` — conventional arrangement (baseline comparison)
- `heavy_wake` — heavy aircraft in optimal wake position
- `uniform` — all aircraft identical

### 6. Cost (`wingz/cost/`)

Two independent cost models behind the same interface. Cost modeling is a research
area — these will evolve as data becomes available.

#### `mass_proxy.py`
Cost score as weighted function of structural mass + control hardware mass + complexity
factor. No dollar values needed.

#### `materials.py`
Bottom-up estimate from component costs: carbon fiber $/kg, solar cells $/W, avionics
component pricing (GPS modules, IMUs, radios have real prices), assembly labor estimate.

### 7. Mission (`wingz/mission/`)

#### `profiles.py`
Two mission profiles:
1. **HALE 20 km** — ρ ≈ 0.089 kg/m³, V ≈ 25 m/s, calm, near-space solar flux
2. **Lower-altitude LE** — ρ ≈ 0.5-1.0 kg/m³, higher speeds, more turbulence, less solar

#### `endurance.py`
Integrates power model over 24h cycle. Binary answer: does the aircraft close the
energy balance? If yes, it can fly indefinitely (30+ days). If no, it can't.

### 8. Evaluation (`wingz/evaluation/`)

#### `sweep.py` — Parameter Sweep Engine

Sweepable parameters:
- Span per aircraft
- N (fleet size: 1-10)
- Formation architecture (leader/follower, tiered, mesh)
- Position strategy (heavy_front, heavy_wake, uniform)
- Formation spacing (lateral overlap ratio)
- Formation geometry (V, echelon, inline)
- Mission profile (HALE, lower-altitude)
- Structure model (empirical, future beam)
- Cost model (mass proxy, materials)

#### `pareto.py`
Multi-objective Pareto analysis across: endurance feasibility, total mass, cost score,
total drag.

### 9. Visualization (`wingz/visualization/`)

Reusable matplotlib plotting functions:
- Cost vs. drag scatter (current plot, enhanced with architecture coloring)
- Pareto frontiers colored by architecture and position strategy
- Sensitivity spider plots (which parameter matters most?)
- Energy balance timeline (24h cycle: solar input vs. power required)
- Formation geometry diagrams (top-down view of aircraft positions)
- Structural scaling curves (mass vs. span with real aircraft data points)

## Sweepable Parameters Summary

| Parameter | Values | Notes |
|-----------|--------|-------|
| Span per aircraft | 5-80 m | Full range, empirical model flags extrapolation |
| Fleet size N | 1-10 | N=1 is the single-aircraft baseline |
| Formation architecture | leader/follower, tiered, mesh | Each has different mass/resilience profile |
| Position strategy | heavy_front, heavy_wake, uniform | Key thesis test |
| Lateral spacing | -0.2 to 1.0 span overlap | Negative = overlap, positive = gap |
| Formation geometry | V, echelon, inline | Affects which aircraft get wake benefit |
| Mission profile | HALE 20km, lower-altitude LE | Two altitude regimes |
| Altitude | 0-20 km | ISA atmosphere model; density/pressure computed from altitude |
| Aspect ratio | Independent of span | AR can be fixed or swept separately from span |
| Payload mass | kg | Explicit input; payload capacity is a key output metric |
| Latitude | 0-60° | Drives solar availability |
| Season | Summer/equinox/winter solstice | Worst case for endurance closure |

## Future Ideas (Not In Scope)

- **Tethering** — physical cables between aircraft for power transfer. Tether drag is
  significant at these scales but worth investigating later if power sharing proves
  valuable.
- **Analytical beam model** — Euler-Bernoulli spar sizing, to be built once empirical
  results identify promising design regions.
- **CFD validation** — higher-fidelity formation aero if classical results prove insufficient.
- **Dynamic simulation** — time-domain formation control, gust response.

## Key Outputs

The modeling should answer:
1. At what fleet size N does formation become lighter than a single aircraft of equivalent
   aerodynamic performance?
2. At what fleet size does formation become cheaper?
3. How much does position strategy (heavy_wake vs. heavy_front) affect the answer?
4. Which formation architecture works best at which scale?
5. What latitude/season limits exist for 30-day endurance?
6. Which parameters matter most? (sensitivity analysis)
7. Is the thesis true — and if so, under what conditions?
