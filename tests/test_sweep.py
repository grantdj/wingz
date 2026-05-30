import numpy as np
from wingz.evaluation.sweep import (
    AircraftConfig,
    evaluate_config,
    sweep_configs,
    PositionStrategy,
)
from wingz.mission.profiles import hale_20km
from wingz.control.architectures import FormationArchitecture
from wingz.aerodynamics.formation_aero import FormationGeometry


def test_evaluate_single_aircraft():
    config = AircraftConfig(
        N=1, span_each_m=30.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.UNIFORM,
        geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.1,
    )
    result = evaluate_config(config, hale_20km())
    assert result["N"] == 1
    assert result["total_drag_N"] > 0
    assert result["wing_mass_total_kg"] > 0


def test_evaluate_formation():
    config = AircraftConfig(
        N=4, span_each_m=15.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.HEAVY_WAKE,
        geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.1,
    )
    result = evaluate_config(config, hale_20km())
    assert result["N"] == 4
    assert result["architecture"] == "leader_follower"
    assert result["position_strategy"] == "heavy_wake"
    assert result["total_drag_N"] > 0
    assert result["control_mass_total_kg"] > 0


def test_sweep_produces_rows():
    configs = sweep_configs(
        spans=[10.0, 20.0],
        Ns=[1, 3],
        architectures=[FormationArchitecture.LEADER_FOLLOWER],
        position_strategies=[PositionStrategy.UNIFORM],
        geometries=[FormationGeometry.V],
        lateral_overlap_ratios=[0.1],
    )
    results = [evaluate_config(c, hale_20km()) for c in configs]
    assert len(results) == 4


def test_heavy_wake_vs_heavy_front_different():
    config_wake = AircraftConfig(
        N=4, span_each_m=15.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.HEAVY_WAKE,
        geometry=FormationGeometry.V, lateral_overlap_ratio=0.1,
    )
    config_front = AircraftConfig(
        N=4, span_each_m=15.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.HEAVY_FRONT,
        geometry=FormationGeometry.V, lateral_overlap_ratio=0.1,
    )
    r_wake = evaluate_config(config_wake, hale_20km())
    r_front = evaluate_config(config_front, hale_20km())
    assert r_wake["total_drag_N"] != r_front["total_drag_N"]
