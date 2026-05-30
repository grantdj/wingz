import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from wingz.visualization.plots import (
    plot_cost_vs_drag,
    plot_structural_scaling,
    plot_formation_geometry,
)


def test_cost_vs_drag_returns_figure():
    df = pd.DataFrame([
        {"cost_score": 100, "total_drag_N": 50, "N": 1, "architecture": "single"},
        {"cost_score": 80, "total_drag_N": 40, "N": 3, "architecture": "leader_follower"},
    ])
    fig, ax = plot_cost_vs_drag(df)
    assert fig is not None
    assert ax is not None
    plt.close(fig)


def test_structural_scaling_returns_figure():
    fig, ax = plot_structural_scaling()
    assert fig is not None
    plt.close(fig)


def test_formation_geometry_returns_figure():
    fig, ax = plot_formation_geometry(N=5, span_m=10.0, lateral_overlap_ratio=0.1, geometry="v")
    assert fig is not None
    plt.close(fig)
