#!/usr/bin/env python3
"""
Generate docs/formation_flight/results.md from current model state.

Run this after any model changes to update the documented results.
The output is a reproducible snapshot — re-run to see how results
change as models improve.

Usage:
    python scripts/generate_results.py
"""

import datetime
import numpy as np
import pandas as pd

from wingz.evaluation.sweep import (
    AircraftConfig, PositionStrategy, evaluate_config, sweep_configs,
)
from wingz.evaluation.pareto import pareto_filter
from wingz.mission.profiles import hale_20km, lower_altitude_le
from wingz.mission.atmosphere import mission_at_altitude
from wingz.mission.payload import no_payload, surveillance_payload
from wingz.control.architectures import FormationArchitecture
from wingz.aerodynamics.formation_aero import FormationGeometry
from wingz.structures.empirical import EmpiricalStructure, SOLAR_HALE_DATA


REFERENCE_CASES = [
    ("Single 60m", AircraftConfig(
        N=1, span_each_m=60, architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.UNIFORM, geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.0)),
    ("Single 40m", AircraftConfig(
        N=1, span_each_m=40, architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.UNIFORM, geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.0)),
    ("2x20m V (heavy_wake)", AircraftConfig(
        N=2, span_each_m=20, architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.HEAVY_WAKE, geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.1)),
    ("3x15m V (heavy_wake)", AircraftConfig(
        N=3, span_each_m=15, architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.HEAVY_WAKE, geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.1)),
    ("4x15m V (heavy_wake)", AircraftConfig(
        N=4, span_each_m=15, architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.HEAVY_WAKE, geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.1)),
    ("4x15m V (heavy_front)", AircraftConfig(
        N=4, span_each_m=15, architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.HEAVY_FRONT, geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.1)),
    ("4x15m V (uniform/mesh)", AircraftConfig(
        N=4, span_each_m=15, architecture=FormationArchitecture.MESH,
        position_strategy=PositionStrategy.UNIFORM, geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.1)),
    ("6x10m V (heavy_wake)", AircraftConfig(
        N=6, span_each_m=10, architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.HEAVY_WAKE, geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.1)),
]

ALTITUDE_CASES_M = [12000, 16000, 20000]

PAYLOAD_CASES = [
    ("no payload", no_payload()),
    ("surveillance", surveillance_payload()),
]


def reference_comparisons(mission):
    """Head-to-head comparisons at specific design points."""
    rows = []
    for name, config in REFERENCE_CASES:
        r = evaluate_config(config, mission)
        r["case"] = name
        rows.append(r)
    return pd.DataFrame(rows)


def position_strategy_comparison(mission):
    """Show impact of position strategy for a fixed formation."""
    results = []
    for strategy in PositionStrategy:
        config = AircraftConfig(
            N=4, span_each_m=15, architecture=FormationArchitecture.LEADER_FOLLOWER,
            position_strategy=strategy, geometry=FormationGeometry.V,
            lateral_overlap_ratio=0.1,
        )
        r = evaluate_config(config, mission)
        r["strategy"] = strategy.value
        results.append(r)
    return pd.DataFrame(results)


def altitude_comparison():
    """Same 4x15m formation evaluated at multiple altitudes."""
    rows = []
    for alt in ALTITUDE_CASES_M:
        mission = mission_at_altitude(alt)
        config = AircraftConfig(
            N=4, span_each_m=15, architecture=FormationArchitecture.LEADER_FOLLOWER,
            position_strategy=PositionStrategy.HEAVY_WAKE, geometry=FormationGeometry.V,
            lateral_overlap_ratio=0.1,
        )
        r = evaluate_config(config, mission)
        r["altitude_label"] = f"{alt//1000}km"
        rows.append(r)
    return pd.DataFrame(rows)


def payload_capacity_comparison(mission):
    """Show mass margin and energy impact across payload options."""
    rows = []
    for label, payload in PAYLOAD_CASES:
        config = AircraftConfig(
            N=4, span_each_m=15, architecture=FormationArchitecture.LEADER_FOLLOWER,
            position_strategy=PositionStrategy.HEAVY_WAKE, geometry=FormationGeometry.V,
            lateral_overlap_ratio=0.1,
            payload=payload,
        )
        r = evaluate_config(config, mission)
        r["payload_label"] = label
        rows.append(r)
    return pd.DataFrame(rows)


def feasibility_flag(energy_closes: bool) -> str:
    return "" if energy_closes else " [INFEASIBLE]"


def main():
    mission = hale_20km()
    structure = EmpiricalStructure.from_data(SOLAR_HALE_DATA)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    lines.append("# Formation Flight — Model Results")
    lines.append("")
    lines.append(f"*Auto-generated by `scripts/generate_results.py` on {now}.*")
    lines.append("*Re-run after model changes to update.*")
    lines.append("")

    # Structural model
    lines.append("## Structural Model")
    lines.append("")
    lines.append(f"Power-law fit: `m_wing = {structure.coefficient:.6f} * b^{structure.exponent:.3f}`")
    lines.append(f"- Data range: {structure.min_span:.0f}–{structure.max_span:.0f} m span")
    lines.append(f"- Exponent {structure.exponent:.3f} confirms superlinear scaling")
    lines.append("")

    # Reference comparisons
    lines.append("## Reference Comparisons (HALE 20km)")
    lines.append("")
    df = reference_comparisons(mission)
    cols = ["case", "N", "span_each_m", "effective_span_m", "total_mass_kg",
            "wing_mass_total_kg", "control_mass_total_kg", "total_drag_N",
            "total_power_W", "cost_score",
            "energy_closes", "battery_mass_kg", "energy_surplus_Wh"]
    table = df[cols].copy()
    table.columns = ["Config", "N", "Span(m)", "Eff.Span(m)", "Mass(kg)",
                     "Wing(kg)", "Ctrl(kg)", "Drag(N)", "Power(W)", "Cost",
                     "EnergyOK", "Battery(kg)", "Surplus(Wh)"]

    # Flag infeasible configs in Config column
    table["Config"] = table.apply(
        lambda row: row["Config"] + feasibility_flag(row["EnergyOK"]), axis=1
    )

    for col in ["Eff.Span(m)", "Mass(kg)", "Wing(kg)", "Ctrl(kg)", "Drag(N)", "Power(W)", "Cost"]:
        table[col] = table[col].map(lambda x: f"{x:.1f}")
    table["Battery(kg)"] = table["Battery(kg)"].map(lambda x: f"{x:.2f}")
    table["Surplus(Wh)"] = table["Surplus(Wh)"].map(lambda x: f"{x:.0f}")

    display_cols = ["Config", "N", "Span(m)", "Eff.Span(m)", "Mass(kg)",
                    "Wing(kg)", "Ctrl(kg)", "Drag(N)", "Power(W)", "Cost",
                    "Battery(kg)", "Surplus(Wh)"]
    lines.append("| " + " | ".join(display_cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(display_cols)) + " |")
    for _, row in table.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in display_cols) + " |")
    lines.append("")
    lines.append("*`[INFEASIBLE]` = energy balance does not close (battery would need to be infinite).*")
    lines.append("")

    # Key findings
    single_60 = df[df["case"] == "Single 60m"].iloc[0]
    form_4x15 = df[df["case"] == "4x15m V (heavy_wake)"].iloc[0]
    mass_saving = (1 - form_4x15["total_mass_kg"] / single_60["total_mass_kg"]) * 100
    drag_saving = (1 - form_4x15["total_drag_N"] / single_60["total_drag_N"]) * 100
    power_change = (form_4x15["total_power_W"] / single_60["total_power_W"] - 1) * 100

    lines.append("### Key Findings")
    lines.append("")
    lines.append(f"**4x15m formation vs. single 60m aircraft:**")
    lines.append(f"- Mass savings: {mass_saving:.1f}%")
    lines.append(f"- Drag reduction: {drag_saving:.1f}%")
    lines.append(f"- Power change: {power_change:+.1f}%")
    lines.append(f"- 4x15m energy closes: {form_4x15['energy_closes']} "
                 f"(surplus {form_4x15['energy_surplus_Wh']:.0f} Wh, "
                 f"battery {form_4x15['battery_mass_kg']:.2f} kg)")
    lines.append(f"- Single 60m energy closes: {single_60['energy_closes']} "
                 f"(surplus {single_60['energy_surplus_Wh']:.0f} Wh, "
                 f"battery {single_60['battery_mass_kg']:.2f} kg)")
    lines.append("")

    # Position strategy
    lines.append("## Position Strategy Impact")
    lines.append("")
    lines.append("4x15m leader/follower, V formation, 10% overlap:")
    lines.append("")
    ps = position_strategy_comparison(mission)
    ps_cols = ["strategy", "total_drag_N", "total_power_W", "cost_score",
               "energy_closes", "battery_mass_kg", "energy_surplus_Wh"]
    ps_table = ps[ps_cols].copy()
    ps_table.columns = ["Strategy", "Drag(N)", "Power(W)", "Cost", "EnergyOK", "Battery(kg)", "Surplus(Wh)"]
    ps_table["Strategy"] = ps_table.apply(
        lambda row: row["Strategy"] + feasibility_flag(row["EnergyOK"]), axis=1
    )
    for col in ["Drag(N)", "Power(W)", "Cost"]:
        ps_table[col] = ps_table[col].map(lambda x: f"{x:.2f}")
    ps_table["Battery(kg)"] = ps_table["Battery(kg)"].map(lambda x: f"{x:.2f}")
    ps_table["Surplus(Wh)"] = ps_table["Surplus(Wh)"].map(lambda x: f"{x:.0f}")
    display_ps = ["Strategy", "Drag(N)", "Power(W)", "Cost", "Battery(kg)", "Surplus(Wh)"]
    lines.append("| " + " | ".join(display_ps) + " |")
    lines.append("| " + " | ".join(["---"] * len(display_ps)) + " |")
    for _, row in ps_table.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in display_ps) + " |")
    lines.append("")

    # Altitude comparison
    lines.append("## Altitude Comparison (4x15m heavy_wake, V, 10% overlap)")
    lines.append("")
    lines.append("Same configuration evaluated across mission altitudes:")
    lines.append("")
    alt_df = altitude_comparison()
    alt_cols = ["altitude_label", "altitude_m", "total_drag_N", "total_power_W",
                "total_mass_kg", "battery_mass_kg", "energy_closes", "energy_surplus_Wh", "day_hours"]
    alt_table = alt_df[alt_cols].copy()
    alt_table.columns = ["Alt", "Alt(m)", "Drag(N)", "Power(W)", "Mass(kg)",
                          "Battery(kg)", "EnergyOK", "Surplus(Wh)", "Day(h)"]
    alt_table["Alt"] = alt_table.apply(
        lambda row: row["Alt"] + feasibility_flag(row["EnergyOK"]), axis=1
    )
    for col in ["Drag(N)", "Power(W)", "Mass(kg)"]:
        alt_table[col] = alt_table[col].map(lambda x: f"{x:.1f}")
    alt_table["Battery(kg)"] = alt_table["Battery(kg)"].map(lambda x: f"{x:.2f}")
    alt_table["Surplus(Wh)"] = alt_table["Surplus(Wh)"].map(lambda x: f"{x:.0f}")
    alt_table["Day(h)"] = alt_table["Day(h)"].map(lambda x: f"{x:.1f}")
    display_alt = ["Alt", "Alt(m)", "Drag(N)", "Power(W)", "Mass(kg)", "Battery(kg)", "Surplus(Wh)", "Day(h)"]
    lines.append("| " + " | ".join(display_alt) + " |")
    lines.append("| " + " | ".join(["---"] * len(display_alt)) + " |")
    for _, row in alt_table.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in display_alt) + " |")
    lines.append("")

    # Payload capacity
    lines.append("## Payload Capacity (4x15m heavy_wake, 20km)")
    lines.append("")
    lines.append("Mass margin and energy impact across payload options:")
    lines.append("")
    pay_df = payload_capacity_comparison(mission)
    pay_cols = ["payload_label", "payload_mass_kg", "payload_power_W",
                "total_mass_kg", "total_mass_with_battery_kg",
                "battery_mass_kg", "energy_closes", "energy_surplus_Wh"]
    pay_table = pay_df[pay_cols].copy()
    pay_table.columns = ["Payload", "PldMass(kg)", "PldPwr(W)", "TotalMass(kg)",
                          "MassWithBatt(kg)", "Battery(kg)", "EnergyOK", "Surplus(Wh)"]
    pay_table["Payload"] = pay_table.apply(
        lambda row: row["Payload"] + feasibility_flag(row["EnergyOK"]), axis=1
    )
    for col in ["TotalMass(kg)", "MassWithBatt(kg)"]:
        pay_table[col] = pay_table[col].map(lambda x: f"{x:.1f}")
    pay_table["Battery(kg)"] = pay_table["Battery(kg)"].map(lambda x: f"{x:.2f}")
    pay_table["Surplus(Wh)"] = pay_table["Surplus(Wh)"].map(lambda x: f"{x:.0f}")
    display_pay = ["Payload", "PldMass(kg)", "PldPwr(W)", "TotalMass(kg)",
                   "MassWithBatt(kg)", "Battery(kg)", "Surplus(Wh)"]
    lines.append("| " + " | ".join(display_pay) + " |")
    lines.append("| " + " | ".join(["---"] * len(display_pay)) + " |")
    for _, row in pay_table.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in display_pay) + " |")
    lines.append("")

    # Model assumptions
    lines.append("## Model Assumptions")
    lines.append("")
    lines.append(f"- Mission: {mission.name}, altitude {mission.altitude_m}m")
    lines.append(f"- Air density: {mission.rho} kg/m³, velocity: {mission.velocity} m/s")
    lines.append(f"- Oswald efficiency: {mission.oswald_e}, CD0: {mission.cd0}")
    lines.append(f"- Wing loading: {mission.wing_loading_N_m2} N/m²")
    lines.append(f"- Formation drag model: Gaussian wake benefit, optimal overlap ~10%")
    lines.append(f"- Leader hardware: ~2.5 kg, 15W; Follower: ~0.4 kg, 3W")
    lines.append(f"- Station-keeping tolerance: 2.0 m")
    lines.append(f"- Energy balance: latitude 30°, day of year 172 (summer solstice)")
    lines.append(f"- Solar panel coverage: 80%, efficiency: 25%")
    lines.append("")
    lines.append("## Caveats")
    lines.append("")
    lines.append("- Wing mass estimates are based on limited public data (all marked 'estimated')")
    lines.append("- Formation drag model uses simplified Gaussian wake interaction, not full vortex lattice")
    lines.append("- Cost model is mass-proxy only — no dollar values")
    lines.append("- Energy balance uses simplified solar irradiance model")
    lines.append("- No dynamic effects (gusts, control latency, failure modes)")
    lines.append("")

    output = "\n".join(lines)
    output_path = "docs/formation_flight/results.md"
    with open(output_path, "w") as f:
        f.write(output)
    print(f"Written to {output_path}")
    print(f"\nKey result: 4x15m formation saves {mass_saving:.1f}% mass, {drag_saving:.1f}% drag vs single 60m")


if __name__ == "__main__":
    main()
