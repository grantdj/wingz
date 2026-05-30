#!/usr/bin/env python3
"""
Sensitivity analysis: vary one parameter at a time, plot impact on total drag and cost.

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
from wingz.mission.profiles import hale_20km
from wingz.control.architectures import FormationArchitecture
from wingz.aerodynamics.formation_aero import FormationGeometry


def baseline_config() -> AircraftConfig:
    return AircraftConfig(
        N=4, span_each_m=20.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.HEAVY_WAKE,
        geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.1,
    )


def vary_parameter(name: str, values, mission):
    results = []
    for v in values:
        config = baseline_config()
        if name == "N":
            config.N = int(v)
        elif name == "span_each_m":
            config.span_each_m = float(v)
        elif name == "lateral_overlap_ratio":
            config.lateral_overlap_ratio = float(v)
        result = evaluate_config(config, mission)
        result["varied_param"] = name
        result["varied_value"] = v
        results.append(result)
    return results


def main():
    save = "--save" in sys.argv

    if save:
        matplotlib.use("Agg")

    mission = hale_20km()

    parameters = {
        "N": np.arange(1, 11),
        "span_each_m": np.linspace(8, 50, 30),
        "lateral_overlap_ratio": np.linspace(-0.1, 0.4, 30),
    }

    fig, axes = plt.subplots(len(parameters), 2, figsize=(14, 4 * len(parameters)))

    for i, (name, values) in enumerate(parameters.items()):
        results = vary_parameter(name, values, mission)
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

    plt.suptitle("Sensitivity Analysis — Formation Flight", fontsize=14, y=1.02)
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
