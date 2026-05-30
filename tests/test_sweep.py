import numpy as np
from wingz.evaluation.sweep import (
    AircraftConfig,
    evaluate_config,
    sweep_configs,
    PositionStrategy,
)
from wingz.mission.profiles import hale_20km
from wingz.mission.atmosphere import mission_at_altitude
from wingz.mission.payload import Payload, surveillance_payload, no_payload
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


# --- New: energy balance integration ---

def test_energy_balance_in_results():
    config = AircraftConfig(
        N=1, span_each_m=30.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.UNIFORM,
        geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.0,
    )
    result = evaluate_config(config, hale_20km())
    assert "energy_closes" in result
    assert "energy_surplus_Wh" in result
    assert "battery_mass_kg" in result
    assert "energy_available_Wh" in result
    assert result["battery_mass_kg"] > 0
    assert result["day_hours"] > 0


# --- New: aspect ratio sweep ---

def test_aspect_ratio_affects_drag():
    config_low_ar = AircraftConfig(
        N=1, span_each_m=30.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.UNIFORM,
        geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.0,
        aspect_ratio=10.0,
    )
    config_high_ar = AircraftConfig(
        N=1, span_each_m=30.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.UNIFORM,
        geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.0,
        aspect_ratio=25.0,
    )
    r_low = evaluate_config(config_low_ar, hale_20km())
    r_high = evaluate_config(config_high_ar, hale_20km())
    # Higher AR = less wing area = less parasite drag
    assert r_high["total_wing_area_m2"] < r_low["total_wing_area_m2"]
    assert r_high["parasite_drag_N"] < r_low["parasite_drag_N"]
    assert r_low["aspect_ratio"] == 10.0
    assert r_high["aspect_ratio"] == 25.0


def test_aspect_ratio_in_sweep():
    configs = sweep_configs(
        spans=[20.0],
        Ns=[1],
        architectures=[FormationArchitecture.LEADER_FOLLOWER],
        position_strategies=[PositionStrategy.UNIFORM],
        geometries=[FormationGeometry.V],
        lateral_overlap_ratios=[0.1],
        aspect_ratios=[10.0, 20.0],
    )
    assert len(configs) == 2


# --- New: altitude sweep ---

def test_altitude_sweep():
    config = AircraftConfig(
        N=1, span_each_m=30.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.UNIFORM,
        geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.0,
    )
    r_12 = evaluate_config(config, mission_at_altitude(12000))
    r_20 = evaluate_config(config, mission_at_altitude(20000))
    assert r_12["altitude_m"] == 12000
    assert r_20["altitude_m"] == 20000
    # Lower altitude = denser air = more parasite drag
    assert r_12["parasite_drag_N"] > r_20["parasite_drag_N"]


# --- New: payload ---

def test_payload_in_results():
    payload = surveillance_payload()
    config = AircraftConfig(
        N=1, span_each_m=30.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.UNIFORM,
        geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.0,
        payload=payload,
    )
    result = evaluate_config(config, hale_20km())
    assert result["payload_mass_kg"] == payload.mass_kg
    assert result["payload_power_W"] == payload.power_W
    assert result["payload_power_total_W"] == payload.power_W


def test_payload_increases_mass_and_power():
    config_no = AircraftConfig(
        N=1, span_each_m=30.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.UNIFORM,
        geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.0,
    )
    config_with = AircraftConfig(
        N=1, span_each_m=30.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.UNIFORM,
        geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.0,
        payload=surveillance_payload(),
    )
    r_no = evaluate_config(config_no, hale_20km())
    r_with = evaluate_config(config_with, hale_20km())
    assert r_with["total_mass_kg"] > r_no["total_mass_kg"]
    assert r_with["total_power_W"] > r_no["total_power_W"]


def test_payload_in_sweep():
    configs = sweep_configs(
        spans=[20.0],
        Ns=[1],
        architectures=[FormationArchitecture.LEADER_FOLLOWER],
        position_strategies=[PositionStrategy.UNIFORM],
        geometries=[FormationGeometry.V],
        lateral_overlap_ratios=[0.1],
        payloads=[no_payload(), surveillance_payload()],
    )
    assert len(configs) == 2
