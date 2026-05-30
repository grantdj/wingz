"""
Formation architecture definitions.
Each architecture defines what hardware each aircraft carries and therefore
the mass and power cost of the control system per aircraft.
"""

import enum
import math


class FormationArchitecture(enum.Enum):
    LEADER_FOLLOWER = "leader_follower"
    TIERED = "tiered"
    MESH = "mesh"


class AircraftRole(enum.Enum):
    LEADER = "leader"
    SUB_LEADER = "sub_leader"
    FOLLOWER = "follower"
    PEER = "peer"


_HARDWARE_MASS = {
    FormationArchitecture.LEADER_FOLLOWER: {
        AircraftRole.LEADER: 2.5,
        AircraftRole.FOLLOWER: 0.4,
    },
    FormationArchitecture.TIERED: {
        AircraftRole.LEADER: 2.5,
        AircraftRole.SUB_LEADER: 1.5,
        AircraftRole.FOLLOWER: 0.4,
    },
    FormationArchitecture.MESH: {
        AircraftRole.PEER: 1.0,
    },
}

_HARDWARE_POWER = {
    FormationArchitecture.LEADER_FOLLOWER: {
        AircraftRole.LEADER: 15.0,
        AircraftRole.FOLLOWER: 3.0,
    },
    FormationArchitecture.TIERED: {
        AircraftRole.LEADER: 15.0,
        AircraftRole.SUB_LEADER: 10.0,
        AircraftRole.FOLLOWER: 3.0,
    },
    FormationArchitecture.MESH: {
        AircraftRole.PEER: 8.0,
    },
}


def get_hardware_mass(arch: FormationArchitecture, role: AircraftRole) -> float:
    role_map = _HARDWARE_MASS[arch]
    if role in role_map:
        return role_map[role]
    # Mesh: all roles map to PEER
    return role_map[AircraftRole.PEER]


def get_hardware_power(arch: FormationArchitecture, role: AircraftRole) -> float:
    role_map = _HARDWARE_POWER[arch]
    if role in role_map:
        return role_map[role]
    return role_map[AircraftRole.PEER]


def assign_roles(arch: FormationArchitecture, N: int) -> list[AircraftRole]:
    if N == 1:
        return [AircraftRole.LEADER]
    if arch == FormationArchitecture.LEADER_FOLLOWER:
        return [AircraftRole.LEADER] + [AircraftRole.FOLLOWER] * (N - 1)
    if arch == FormationArchitecture.TIERED:
        n_sub = max(1, math.ceil((N - 1) / 4))
        n_follow = N - 1 - n_sub
        return [AircraftRole.LEADER] + [AircraftRole.SUB_LEADER] * n_sub + [AircraftRole.FOLLOWER] * n_follow
    return [AircraftRole.PEER] * N
