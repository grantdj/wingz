#!/usr/bin/env python3
"""
Sensitivity analysis: vary one parameter at a time, plot impact on total drag and cost.

Now includes altitude, aspect ratio, and payload mass sensitivity.

Usage:
    python scripts/sensitivity_analysis.py
    python scripts/sensitivity_analysis.py --save
"""

import sys
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

from wingz.evaluation.sweep import AircraftConfig, PositionStrategy, evaluate_config
from wingz.mission.atmosphere import mission_at_altitude
from wingz.mission.payload import Payload
from wingz.control.architectures import FormationArchitecture
from wingz.aerodynamics.formation_aero import FormationGeometry


def baseline_config() -> AircraftConfig:
    return AircraftConfig(
        N=4, span_each_m=20.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.HEAVY_WAKE,
        geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.1,
        aspect_ratio=18.0,
        payload=Payload(name="none", mass_kg=0.0, power_W=0.0),
    )


BASELINE_ALTITUDE_M = 16000


def vary_parameter(name: str, values, base_altitude_m: float = BASELINE_ALTITUDE_M):
    results = []
    for v in values:
        config = baseline_config()
        altitude_m = base_altitude_m

        if name == "N":
            config.N = int(v)
        elif name == "span_each_m":
            config.span_each_m = float(v)
        elif name == "lateral_overlap_ratio":
            config.lateral_overlap_ratio = float(v)
        elif name == "altitude_m":
            altitude_m = float(v)
        elif name == "aspect_ratio":
            config.aspect_ratio = float(v)
        elif name == "payload_mass_kg":
            config.payload = Payload(name="custom", mass_kg=float(v), power_W=float(v) * 5.0)

        mission = mission_at_altitude(altitude_m)
        result = evaluate_config(config, mission)
        result["varied_param"] = name
        result["varied_value"] = v
        results.append(result)
    return results


def main():
    save = "--save" in sys.argv

    if save:
        matplotlib.use("Agg")

    parameters = {
        "N": np.arange(1, 11),
        "span_each_m": np.linspace(8, 50, 30),
        "lateral_overlap_ratio": np.linspace(-0.1, 0.4, 30),
        "altitude_m": np.linspace(8000, 20000, 25),
        "aspect_ratio": np.linspace(8, 30, 25),
        "payload_mass_kg": np.linspace(0, 20, 21),
    }

    n_params = len(parameters)
    fig, axes = plt.subplots(n_params, 3, figsize=(18, 4 * n_params))

    for i, (name, values) in enumerate(parameters.items()):
        results = vary_parameter(name, values)
        df = pd.DataFrame(results)

        axes[i, 0].plot(df["varied_value"], df["total_drag_N"], "b.-")
        axes[i, 0].set_xlabel(name)
        axes[i, 0].set_ylabel("Total drag (N)")
        axes[i, 0].set_title(f"Drag sensitivity to {name}")
        axes[i, 0].grid(True, alpha=0.3)

        axes[i, 1].plot(df["varied_value"], df["cost_score"], "r.-")
        axes[i, 1].set_xlabel(name)
        axes[i, 1].set_ylabel("Cost score")
        axes[i, 1].set_title(f"Cost sensitivity to {name}")
        axes[i, 1].grid(True, alpha=0.3)

        # Third column: energy balance metric
        # Show energy_surplus_Wh, colored green/red by energy_closes
        colors = ["green" if c else "red" for c in df["energy_closes"]]
        axes[i, 2].scatter(df["varied_value"], df["energy_surplus_Wh"], c=colors, s=20, alpha=0.7)
        axes[i, 2].axhline(0, color="black", linewidth=0.8, linestyle="--")
        axes[i, 2].set_xlabel(name)
        axes[i, 2].set_ylabel("Energy surplus (Wh)")
        axes[i, 2].set_title(f"Energy balance sensitivity to {name}")
        axes[i, 2].grid(True, alpha=0.3)

    plt.suptitle("Sensitivity Analysis — Formation Flight", fontsize=14, y=1.01)
    plt.tight_layout()

    if save:
        import os
        os.makedirs("docs/formation_flight", exist_ok=True)
        fig.savefig("docs/formation_flight/sensitivity_analysis.png", dpi=150, bbox_inches="tight")
        print("Saved to docs/formation_flight/sensitivity_analysis.png")
    else:
        plt.show()


if __name__ == "__main__":
    main()
