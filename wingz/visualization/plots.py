"""Reusable matplotlib plotting functions for formation flight analysis."""

from typing import Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from wingz.structures.empirical import EmpiricalStructure, SOLAR_HALE_DATA


def plot_cost_vs_drag(
    df: pd.DataFrame, x_key: str = "cost_score", y_key: str = "total_drag_N",
    color_by: str = "architecture", pareto_df: Optional[pd.DataFrame] = None,
) -> tuple:
    fig, ax = plt.subplots(figsize=(10, 7))
    for label, group in df.groupby(color_by):
        ax.scatter(group[x_key], group[y_key], label=label, alpha=0.6, s=30)
    if pareto_df is not None and len(pareto_df) > 0:
        ax.scatter(pareto_df[x_key], pareto_df[y_key], marker="x", color="black",
                   s=80, linewidths=2, label="Pareto frontier", zorder=5)
    ax.set_xlabel("Cost score")
    ax.set_ylabel("Total drag (N)")
    ax.set_title("Cost vs Drag: Single Aircraft vs Formation")
    ax.legend()
    ax.grid(True, alpha=0.3)
    return fig, ax


def plot_structural_scaling(
    structure: Optional[EmpiricalStructure] = None,
    span_range: tuple = (5, 100),
) -> tuple:
    structure = structure or EmpiricalStructure.from_data(SOLAR_HALE_DATA)
    fig, ax = plt.subplots(figsize=(10, 7))
    spans = np.linspace(span_range[0], span_range[1], 200)
    masses = [structure.wing_mass(s) for s in spans]
    ax.plot(spans, masses, "b-", label=f"Fit: m = {structure.coefficient:.4f} * b^{structure.exponent:.2f}")
    for d in SOLAR_HALE_DATA:
        ax.plot(d["span_m"], d["wing_mass_kg"], "ro", markersize=8)
        ax.annotate(d["name"], (d["span_m"], d["wing_mass_kg"]),
                    textcoords="offset points", xytext=(5, 5), fontsize=8)
    ax.set_xlabel("Wingspan (m)")
    ax.set_ylabel("Wing mass (kg)")
    ax.set_title("Wing Structural Mass Scaling — Solar/HALE Aircraft")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_yscale("log")
    ax.set_xscale("log")
    return fig, ax


def plot_energy_balance_timeline(
    power_required_W: float, peak_solar_power_W: float, day_hours: float,
) -> tuple:
    fig, ax = plt.subplots(figsize=(10, 5))
    hours = np.linspace(0, 24, 500)
    sunrise = 12 - day_hours / 2
    sunset = 12 + day_hours / 2
    solar_power = np.zeros_like(hours)
    daylight = (hours >= sunrise) & (hours <= sunset)
    phase = np.pi * (hours[daylight] - sunrise) / day_hours
    solar_power[daylight] = peak_solar_power_W * np.sin(phase)
    ax.fill_between(hours, solar_power, alpha=0.3, color="gold", label="Solar power")
    ax.axhline(power_required_W, color="red", linestyle="--", label=f"Power required ({power_required_W:.0f} W)")
    ax.fill_between(hours, power_required_W, solar_power,
        where=solar_power > power_required_W, alpha=0.2, color="green", label="Battery charging")
    ax.fill_between(hours, 0, power_required_W,
        where=solar_power < power_required_W, alpha=0.2, color="red", label="Battery discharge")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Power (W)")
    ax.set_title("24-Hour Energy Balance")
    ax.set_xlim(0, 24)
    ax.set_ylim(0, max(peak_solar_power_W * 1.1, power_required_W * 1.5))
    ax.legend()
    ax.grid(True, alpha=0.3)
    return fig, ax


def plot_formation_geometry(
    N: int, span_m: float, lateral_overlap_ratio: float, geometry: str = "v",
) -> tuple:
    fig, ax = plt.subplots(figsize=(8, 8))
    gap = span_m * (1 - lateral_overlap_ratio)
    streamwise_sep = span_m * 2
    positions = []
    if geometry == "v":
        positions.append((0, 0))
        depth = 1
        idx = 1
        while idx < N:
            x_offset = depth * gap
            y_offset = -depth * streamwise_sep
            positions.append((-x_offset, y_offset))
            idx += 1
            if idx < N:
                positions.append((x_offset, y_offset))
                idx += 1
            depth += 1
    elif geometry == "echelon":
        for i in range(N):
            positions.append((i * gap, -i * streamwise_sep))
    else:
        for i in range(N):
            positions.append((0, -i * streamwise_sep))
    for i, (x, y) in enumerate(positions):
        wing_left = x - span_m / 2
        wing_right = x + span_m / 2
        ax.plot([wing_left, wing_right], [y, y], "b-", linewidth=3)
        ax.plot(x, y, "ko", markersize=4)
        label = "L" if i == 0 else f"F{i}"
        ax.annotate(label, (x, y), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=10, fontweight="bold")
    ax.set_aspect("equal")
    ax.set_xlabel("Lateral position (m)")
    ax.set_ylabel("Streamwise position (m)")
    ax.set_title(f"{geometry.upper()} Formation — N={N}, span={span_m}m, overlap={lateral_overlap_ratio:.0%}")
    ax.grid(True, alpha=0.3)
    return fig, ax
