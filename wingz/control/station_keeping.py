"""
Station-keeping energy model.
Estimates additional power required for a follower to maintain formation position.

P_sk = k * turbulence * (1/tolerance) * span^1.5

The span^1.5 exponent reflects that correction forces scale with wing loading
and control surface moment arm. The k=50 constant is calibrated for
order-of-magnitude reasonableness, not validated against flight data.

References:
    Pahle, J. et al., "An Initial Flight Investigation of Formation Flight
        for Drag Reduction on the C-17 Aircraft," AIAA 2012-4802, 2012.
    Hanson, C.E. et al., "The DARPA/NASA Automated Airborne Refueling
        Demonstration," AIAA 2006-6610, 2006.

See docs/formation_flight/references.md for full citations.
"""

from wingz.mission.profiles import MissionProfile


def station_keeping_power(
    mission: MissionProfile,
    span_m: float,
    position_tolerance_m: float,
    is_leader: bool = False,
    in_wake: bool = True,
) -> float:
    """
    Estimate power (watts) for station-keeping.
    Leader has zero cost. Followers correct for turbulence and vortex disturbances.
    P_sk = k * turbulence * (1/tolerance) * span^1.5
    """
    if is_leader:
        return 0.0
    base_turbulence = mission.turbulence_intensity
    wake_factor = 1.5 if in_wake else 1.0
    effective_turbulence = base_turbulence * wake_factor
    k = 50.0
    return k * effective_turbulence * (1.0 / position_tolerance_m) * span_m**1.5
