# wingz

Modeling library for comparing single large-span aircraft vs multi-aircraft formations for solar-powered HALE (High Altitude Long Endurance) platforms.

Explores the tradeoff: is it better to build one big solar wing, or fly several smaller ones in formation to exploit wake-induced drag reduction?

## Modules

| Package | Purpose |
|---------|---------|
| `wingz.aerodynamics` | Drag models, formation aerodynamics (wake vortex interactions) |
| `wingz.structures` | Empirical structural scaling (mass vs span) |
| `wingz.solar` | Solar power models, energy balance over a mission |
| `wingz.cost` | Material cost and mass-proxy cost models |
| `wingz.mission` | Mission profiles (altitude, velocity, duration) |
| `wingz.control` | Formation architectures (leader-follower, mesh) |
| `wingz.evaluation` | Parameter sweeps, Pareto filtering |
| `wingz.visualization` | Matplotlib plots for cost/drag, scaling, geometry, energy |

## Setup

Requires Python 3.11+.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

Run the full parameter sweep comparing single vs formation configurations:

```bash
python scripts/sweep_single_vs_formation.py
```

Run sensitivity analysis (vary one parameter at a time):

```bash
python scripts/sensitivity_analysis.py
```

Pass `--save` to either script to write plots to disk instead of displaying them.

## Project Structure

```
scripts/          Runnable analysis scripts
wingz/            Core library
tests/            Tests (run with pytest)
notebooks/        Jupyter notebooks for exploration
docs/             Design documentation and future ideas
```
