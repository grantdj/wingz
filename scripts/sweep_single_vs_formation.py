#!/usr/bin/env python3
"""
Sweep single aircraft vs formation configurations and plot results.

Now includes altitude sweep, aspect ratio sweep, surveillance payload option,
energy balance feasibility filtering, and a feasible/infeasible config plot.

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
from wingz.mission.atmosphere import mission_at_altitude
from wingz.mission.payload import surveillance_payload, no_payload
from wingz.control.architectures import FormationArchitecture
from wingz.aerodynamics.formation_aero import FormationGeometry
from wingz.visualization.plots import (
    plot_cost_vs_drag, plot_structural_scaling, plot_formation_geometry, plot_energy_balance_timeline,
)

ALTITUDES_M = [12000, 16000, 20000]
ASPECT_RATIOS = [12, 18, 25]


def run_sweep(mission, payload):
    configs = sweep_configs(
        spans=np.linspace(8, 80, 20).tolist(),
        Ns=[1, 2, 3, 4, 6, 8],
        architectures=[FormationArchitecture.LEADER_FOLLOWER, FormationArchitecture.MESH],
        position_strategies=[PositionStrategy.UNIFORM, PositionStrategy.HEAVY_WAKE, PositionStrategy.HEAVY_FRONT],
        geometries=[FormationGeometry.V],
        lateral_overlap_ratios=[0.05, 0.1, 0.15],
        aspect_ratios=ASPECT_RATIOS,
        payloads=[payload],
    )
    results = [evaluate_config(c, mission) for c in configs]
    return pd.DataFrame(results)


def print_energy_summary(df, label=""):
    n_total = len(df)
    n_feasible = df["energy_closes"].sum()
    n_infeasible = n_total - n_feasible
    print(f"\n{'=' * 60}")
    if label:
        print(f"  {label}")
    print(f"  Total configs: {n_total}  |  Feasible: {n_feasible}  |  Infeasible: {n_infeasible}")
    feasible = df[df["energy_closes"]]
    if len(feasible) > 0:
        print(f"  Feasible energy surplus range: "
              f"{feasible['energy_surplus_Wh'].min():.0f} – {feasible['energy_surplus_Wh'].max():.0f} Wh")
        print(f"  Feasible battery mass range: "
              f"{feasible['battery_mass_kg'].min():.1f} – {feasible['battery_mass_kg'].max():.1f} kg")
    print(f"{'=' * 60}")


def main():
    save = "--save" in sys.argv

    if save:
        matplotlib.use("Agg")

    # ------------------------------------------------------------------ #
    # 1. Multi-altitude sweep (no payload)                                #
    # ------------------------------------------------------------------ #
    print("Running altitude sweep (no payload)...")
    alt_dfs = {}
    for alt in ALTITUDES_M:
        mission = mission_at_altitude(alt)
        print(f"  Altitude {alt/1000:.0f}km — evaluating configs...")
        df = run_sweep(mission, no_payload())
        alt_dfs[alt] = df
        print_energy_summary(df, label=f"Altitude {alt/1000:.0f}km, no payload")

    # ------------------------------------------------------------------ #
    # 2. Surveillance payload sweep at 20km                               #
    # ------------------------------------------------------------------ #
    print("\nRunning surveillance payload sweep at 20km...")
    mission_20km = mission_at_altitude(20000)
    df_surveillance = run_sweep(mission_20km, surveillance_payload())
    print_energy_summary(df_surveillance, label="20km, surveillance payload")

    # ------------------------------------------------------------------ #
    # 3. Pareto analysis on feasible configs at 20km (no payload)         #
    # ------------------------------------------------------------------ #
    df_20km = alt_dfs[20000]
    df_feasible = df_20km[df_20km["energy_closes"]].copy()
    df_infeasible = df_20km[~df_20km["energy_closes"]].copy()

    print(f"\n20km no-payload: {len(df_feasible)} feasible, {len(df_infeasible)} infeasible")

    pareto_rows = pareto_filter(df_feasible.to_dict("records")) if len(df_feasible) > 0 else []
    pareto_df = pd.DataFrame(pareto_rows) if pareto_rows else pd.DataFrame()

    print(f"\nPareto frontier (feasible configs only): {len(pareto_df)} configs")
    if len(pareto_df) > 0:
        display_cols = ["N", "span_each_m", "aspect_ratio", "architecture", "position_strategy",
                        "altitude_m", "total_drag_N", "cost_score", "total_mass_kg",
                        "energy_surplus_Wh", "battery_mass_kg"]
        print(pareto_df[display_cols].to_string())

    # ------------------------------------------------------------------ #
    # 4. Plots                                                            #
    # ------------------------------------------------------------------ #
    # Plot A: cost vs drag, colored by architecture (Pareto marked)
    fig1, ax1 = plot_cost_vs_drag(df_feasible, pareto_df=pareto_df if len(pareto_df) > 0 else None)
    ax1.set_title("Cost vs Drag — Feasible Configs, 20km (by Architecture)")

    # Plot B: cost vs drag, colored by position strategy
    fig2, ax2 = plot_cost_vs_drag(df_feasible, color_by="position_strategy",
                                   pareto_df=pareto_df if len(pareto_df) > 0 else None)
    ax2.set_title("Cost vs Drag — by Position Strategy (feasible only)")

    # Plot C: structural scaling
    fig3, ax3 = plot_structural_scaling()

    # Plot D: formation geometry example
    fig4, ax4 = plot_formation_geometry(N=5, span_m=15.0, lateral_overlap_ratio=0.1, geometry="v")

    # Plot E: feasible vs infeasible configs (colored by energy_closes)
    fig5, ax5 = plt.subplots(figsize=(10, 7))
    ax5.scatter(df_infeasible["cost_score"], df_infeasible["total_drag_N"],
                alpha=0.4, s=25, color="red", label=f"Infeasible ({len(df_infeasible)})")
    ax5.scatter(df_feasible["cost_score"], df_feasible["total_drag_N"],
                alpha=0.6, s=25, color="green", label=f"Feasible ({len(df_feasible)})")
    if len(pareto_df) > 0:
        ax5.scatter(pareto_df["cost_score"], pareto_df["total_drag_N"],
                    marker="x", color="black", s=80, linewidths=2,
                    label="Pareto frontier", zorder=5)
    ax5.set_xlabel("Cost score")
    ax5.set_ylabel("Total drag (N)")
    ax5.set_title("Feasible vs Infeasible Configs — 20km, No Payload")
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # Plot F: energy balance across altitudes (feasible fraction per altitude)
    fig6, axes6 = plt.subplots(1, 2, figsize=(14, 6))
    alt_labels = [f"{a//1000}km" for a in ALTITUDES_M]
    feasible_fractions = [alt_dfs[a]["energy_closes"].mean() for a in ALTITUDES_M]
    mean_surplus = [alt_dfs[a][alt_dfs[a]["energy_closes"]]["energy_surplus_Wh"].mean()
                    if alt_dfs[a]["energy_closes"].any() else 0
                    for a in ALTITUDES_M]

    axes6[0].bar(alt_labels, [f * 100 for f in feasible_fractions], color=["#e74c3c", "#f39c12", "#27ae60"])
    axes6[0].set_xlabel("Altitude")
    axes6[0].set_ylabel("Feasible configs (%)")
    axes6[0].set_title("Energy Closure Rate by Altitude")
    axes6[0].grid(True, alpha=0.3, axis="y")

    axes6[1].bar(alt_labels, mean_surplus, color=["#e74c3c", "#f39c12", "#27ae60"])
    axes6[1].set_xlabel("Altitude")
    axes6[1].set_ylabel("Mean energy surplus (Wh)")
    axes6[1].set_title("Mean Energy Surplus (Feasible Configs) by Altitude")
    axes6[1].grid(True, alpha=0.3, axis="y")

    plt.suptitle("Energy Balance by Altitude", fontsize=13)
    plt.tight_layout()

    # Plot G: AR effect on energy closure
    fig7, ax7 = plt.subplots(figsize=(10, 6))
    for ar in ASPECT_RATIOS:
        subset = df_20km[df_20km["aspect_ratio"].round(1) == float(ar)]
        if len(subset) == 0:
            continue
        feasible_pct = subset["energy_closes"].mean() * 100
        ax7.bar(str(ar), feasible_pct, label=f"AR={ar}")
    ax7.set_xlabel("Aspect Ratio")
    ax7.set_ylabel("Feasible configs (%)")
    ax7.set_title("Energy Closure Rate by Aspect Ratio — 20km, No Payload")
    ax7.grid(True, alpha=0.3, axis="y")

    if save:
        import os
        os.makedirs("docs/formation_flight", exist_ok=True)
        fig1.savefig("docs/formation_flight/cost_vs_drag_by_arch.png", dpi=150, bbox_inches="tight")
        fig2.savefig("docs/formation_flight/cost_vs_drag_by_strategy.png", dpi=150, bbox_inches="tight")
        fig3.savefig("docs/formation_flight/structural_scaling.png", dpi=150, bbox_inches="tight")
        fig4.savefig("docs/formation_flight/v_formation_geometry.png", dpi=150, bbox_inches="tight")
        fig5.savefig("docs/formation_flight/feasible_vs_infeasible.png", dpi=150, bbox_inches="tight")
        fig6.savefig("docs/formation_flight/energy_balance_by_altitude.png", dpi=150, bbox_inches="tight")
        fig7.savefig("docs/formation_flight/energy_closure_by_ar.png", dpi=150, bbox_inches="tight")
        print("\nFigures saved to docs/formation_flight/")
    else:
        plt.show()


if __name__ == "__main__":
    main()
