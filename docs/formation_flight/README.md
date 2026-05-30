# Formation Flight Analysis

## Overview

This project models the tradeoff between building one large high-aspect-ratio
solar-powered aircraft vs. flying a formation of smaller aircraft to achieve
equivalent aerodynamic performance.

## Core Thesis

Structural complexity scales faster than aerodynamic benefit as wingspan increases.
Formation flight trades structural complexity for control complexity.

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

### Position Strategy

The heaviest aircraft (full nav/comms) should sit in the best wake position,
not the leader slot. The lightest aircraft leads because it flies in clean
air and has the best power-to-weight ratio to handle full drag.

### Formation Architectures

Three architectures modeled:
- **Leader/follower** — one heavy leader, light followers
- **Tiered** — leader + sub-leaders + followers
- **Mesh** — all aircraft carry partial nav, cooperative localization

### Energy Balance

For 30+ day missions, every aircraft must close a 24-hour energy cycle.
The battery mass feedback loop (more battery → more weight → more drag →
more power → more battery) is the critical sizing constraint.
