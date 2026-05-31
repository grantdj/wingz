# Formation Flight Analysis

## Overview

This project models the tradeoff between building one large high-aspect-ratio
solar-powered aircraft vs. flying a formation of smaller aircraft to achieve
equivalent aerodynamic performance.

## Core Thesis

**The fundamental trade: structural complexity → control complexity.**

As wingspan increases, structural mass grows faster than the aerodynamic benefit
it provides. Wing deflection scales with the cube of span. At extreme wingspans,
wings become stiffness-limited rather than strength-limited — requiring ever more
material just to avoid flutter and excessive deflection, not to carry load.

Formation flight sidesteps this entirely. Instead of one very large wing fighting
nonlinear structural penalties, multiple smaller aircraft fly in coordinated
formation to achieve comparable induced drag performance. Each individual aircraft
stays in the structurally efficient regime while the formation collectively acts
as a larger wing.

The thesis is that autonomous control systems — GPS, IMUs, radios, compute — are
cheaper, lighter, and more scalable than the aerospace structures required to build
extreme-span wings. Control complexity replaces structural complexity.

## Running the Analysis

### Regenerate all plots

```bash
./scripts/run_all.sh          # run all scripts, save plots to docs/
./scripts/run_all.sh --quick  # skip slow sweeps (formation_scaling, span_chord)
```

### Individual scripts

| Script | What it does |
|---|---|
| `converged_sweep.py` | Full converged analysis across 11 configs at max payload |
| `energy_timeline.py` | 24h solar/battery/waste cycle for key configs |
| `cost_comparison.py` | Cost vs payload sweep with realistic pricing |
| `climb_profile.py` | Launch-to-altitude simulation (48h) |
| `formation_drag_analysis.py` | Drag per slot, effective span, overlap, geometry |
| `formation_scaling.py` | $/kg payload vs fleet size N=1-12 |
| `span_chord_sweep.py` | Span × chord heatmaps for $/kg and payload mass |
| `sweep_single_vs_formation.py` | Legacy parameter sweep (old engine) |
| `sensitivity_analysis.py` | Legacy sensitivity analysis (old engine) |

All scripts accept `--save` to write plots to `docs/formation_flight/`.
All use the shared solver (`wingz/evaluation/solver.py`) and constants
(`wingz/constants.py`) — no duplicated physics.

## Package Structure

- `wingz/constants.py` — single source of truth for all design constants
- `wingz/structures/` — wing mass scaling (empirical + beam model)
- `wingz/aerodynamics/` — drag models including formation wake effects
- `wingz/solar/` — solar power and energy balance
- `wingz/control/` — formation architectures and station-keeping
- `wingz/cost/` — mass-proxy and bottom-up cost models with manufacturing capital
- `wingz/mission/` — mission profiles, atmosphere model, payload model
- `wingz/evaluation/` — sweep engine, shared solver, Pareto analysis
- `wingz/visualization/` — matplotlib plotting

## Key Design Insights

### The Navigator Flies From Behind

This inverts the usual intuition where the "leader" is the most capable aircraft.

In a formation, the front aircraft flies in clean air and pays full induced drag.
The first follower slot sits in the upwash of the leader's wingtip vortex — the
aerodynamically best seat in the house.

The key insight: put the **lightest** aircraft up front. It has the best
power-to-weight ratio and can absorb full drag. Put the **heaviest** aircraft
(the one carrying the full navigation and communications stack) in the optimal
wake position where it gets the greatest drag reduction.

This creates a natural synergy that doesn't exist in single-aircraft design:
- The aircraft that needs the most aerodynamic help (heaviest) gets the most
- That same aircraft has the best sensors for precise station-keeping
- And it's in the position where station-keeping precision matters most
  (tight formation spacing = more drag benefit but tighter tolerance)

The formation navigator directs traffic from behind, not from the front.

### Formation Architectures

Three architectures modeled:
- **Leader/follower** — one heavy leader, light followers
- **Tiered** — leader + sub-leaders + followers
- **Mesh** — all aircraft carry partial nav, cooperative localization

### Energy Balance

For 30+ day missions, every aircraft must close a 24-hour energy cycle.
The battery mass feedback loop (more battery → more weight → more drag →
more power → more battery) is the critical sizing constraint.

**Energy closure is the primary feasibility gate in the sweep engine.** A
design is only considered viable if it closes the 24-hour energy cycle; all
other metrics (mass, cost, drag) are secondary to this constraint.

### Payload Capacity

Payload mass and power draw are explicit inputs to the energy balance. Payload
capacity — how much useful payload a design can carry while still closing the
energy balance — is a key output metric alongside cost and total mass.

### Altitude Sweeps

The atmosphere model (`wingz/mission/atmosphere.py`) implements the ISA standard
atmosphere for the troposphere and lower stratosphere (0–20 km). This enables
altitude as a sweep parameter: density, temperature, and pressure are computed
from altitude rather than hard-coded per mission profile.

### Aspect Ratio as Independent Parameter

Aspect ratio (AR) can be swept independently of span. Fixing AR while varying
span (or vice versa) separates the structural and aerodynamic tradeoffs and
allows the sweep engine to explore the full design space more efficiently.
