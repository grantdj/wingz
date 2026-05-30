#!/usr/bin/env python3
"""
Sweep single aircraft vs formation configurations and plot results.

Usage:
    python scripts/sweep_single_vs_formation.py
    python scripts/sweep_single_vs_formation.py --save
"""

import sys
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

from wingz.evaluation.sweep import (
    AircraftConfig, PositionStrategy, evaluate_config, sweep_configs,
)
from wingz.evaluation.pareto import pareto_filter
from wingz.mission.profiles import hale_20km, lower_altitude_le
from wingz.control.architectures import FormationArchitecture
from wingz.aerodynamics.formation_aero import FormationGeometry
from wingz.visualization.plots import (
    plot_cost_vs_drag, plot_structural_scaling, plot_formation_geometry, plot_energy_balance_timeline,
)


def main():
    save = "--save" in sys.argv

    if save:
        matplotlib.use("Agg")

    mission = hale_20km()

    configs = sweep_configs(
        spans=np.linspace(8, 80, 40).tolist(),
        Ns=[1, 2, 3, 4, 6, 8],
        architectures=[FormationArchitecture.LEADER_FOLLOWER, FormationArchitecture.MESH],
        position_strategies=[PositionStrategy.UNIFORM, PositionStrategy.HEAVY_WAKE, PositionStrategy.HEAVY_FRONT],
        geometries=[FormationGeometry.V],
        lateral_overlap_ratios=[0.05, 0.1, 0.15],
    )

    print(f"Evaluating {len(configs)} configurations...")
    results = [evaluate_config(c, mission) for c in configs]
    df = pd.DataFrame(results)

    pareto_rows = pareto_filter(df.to_dict("records"))
    pareto_df = pd.DataFrame(pareto_rows)

    print(f"\nResults: {len(df)} configs, {len(pareto_df)} on Pareto frontier")
    print(f"\nPareto frontier summary:")
    if len(pareto_df) > 0:
        print(pareto_df[["N", "span_each_m", "architecture", "position_strategy",
                          "total_drag_N", "cost_score", "total_mass_kg"]].to_string())

    fig1, ax1 = plot_cost_vs_drag(df, pareto_df=pareto_df)
    fig2, ax2 = plot_cost_vs_drag(df, color_by="position_strategy", pareto_df=pareto_df)
    ax2.set_title("Cost vs Drag — by Position Strategy")
    fig3, ax3 = plot_structural_scaling()
    fig4, ax4 = plot_formation_geometry(N=5, span_m=15.0, lateral_overlap_ratio=0.1, geometry="v")

    if save:
        import os
        os.makedirs("docs/formation_flight", exist_ok=True)
        fig1.savefig("docs/formation_flight/cost_vs_drag_by_arch.png", dpi=150, bbox_inches="tight")
        fig2.savefig("docs/formation_flight/cost_vs_drag_by_strategy.png", dpi=150, bbox_inches="tight")
        fig3.savefig("docs/formation_flight/structural_scaling.png", dpi=150, bbox_inches="tight")
        fig4.savefig("docs/formation_flight/v_formation_geometry.png", dpi=150, bbox_inches="tight")
        print("\nFigures saved to docs/formation_flight/")
    else:
        plt.show()


if __name__ == "__main__":
    main()
