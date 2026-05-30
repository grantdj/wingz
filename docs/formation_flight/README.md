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

### Full parameter sweep

```bash
python scripts/sweep_single_vs_formation.py        # interactive plots
python scripts/sweep_single_vs_formation.py --save  # save to docs/
```

### Sensitivity analysis

```bash
python scripts/sensitivity_analysis.py        # interactive
python scripts/sensitivity_analysis.py --save # save to docs/
```

## Package Structure

- `wingz/structures/` — wing mass scaling models
- `wingz/aerodynamics/` — drag models including formation effects
- `wingz/solar/` — solar power and energy balance
- `wingz/control/` — formation architectures and station-keeping
- `wingz/cost/` — mass-proxy and bottom-up cost models
- `wingz/mission/` — mission profile definitions
- `wingz/evaluation/` — parameter sweeps and Pareto analysis
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
