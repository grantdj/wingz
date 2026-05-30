import numpy as np
from wingz.control.architectures import (
    FormationArchitecture,
    AircraftRole,
    get_hardware_mass,
    get_hardware_power,
    assign_roles,
)


def test_leader_heavier_than_follower_in_leader_follower():
    leader_mass = get_hardware_mass(FormationArchitecture.LEADER_FOLLOWER, AircraftRole.LEADER)
    follower_mass = get_hardware_mass(FormationArchitecture.LEADER_FOLLOWER, AircraftRole.FOLLOWER)
    assert leader_mass > follower_mass


def test_mesh_all_equal():
    mass_a = get_hardware_mass(FormationArchitecture.MESH, AircraftRole.LEADER)
    mass_b = get_hardware_mass(FormationArchitecture.MESH, AircraftRole.FOLLOWER)
    assert mass_a == mass_b


def test_leader_follower_roles():
    roles = assign_roles(FormationArchitecture.LEADER_FOLLOWER, N=4)
    assert roles.count(AircraftRole.LEADER) == 1
    assert roles.count(AircraftRole.FOLLOWER) == 3


def test_tiered_has_sub_leaders():
    roles = assign_roles(FormationArchitecture.TIERED, N=6)
    assert AircraftRole.SUB_LEADER in roles
    assert roles[0] == AircraftRole.LEADER


def test_mesh_all_peers():
    roles = assign_roles(FormationArchitecture.MESH, N=4)
    assert all(r == AircraftRole.PEER for r in roles)


def test_total_hardware_mass():
    roles = assign_roles(FormationArchitecture.LEADER_FOLLOWER, N=4)
    total = sum(get_hardware_mass(FormationArchitecture.LEADER_FOLLOWER, r) for r in roles)
    assert 2.0 < total < 6.0
