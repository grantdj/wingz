"""
Station-keeping energy model.
Estimates additional power required for a follower to maintain formation position.

Station keeping is primarily a servo actuation problem, not a thrust problem.
Trim thrust is already captured by the drag model (D*V). Small thrust
perturbations around trim are negligible in energy terms. The real cost is
continuous control surface deflections to hold lateral/vertical position
against turbulence and wake vortex disturbances.

Model:
    P_sk = n_servos * P_servo_active * duty_cycle

    duty_cycle = clamp(base_duty * turb_scale * tol_scale * wake_factor, 0, 0.9)

    where:
        turb_scale  = turbulence_intensity / 0.1   (normalized to light turbulence)
        tol_scale   = 2.0 / position_tolerance_m   (normalized to 2m baseline)
        wake_factor = 1.5 in wake, 1.0 in clean air

Typical results for a 7m span follower at 2m tolerance:
    Light turbulence (0.1), in wake:  ~3.8 W
    Moderate (0.2), in wake:          ~7.5 W
    Heavy (0.3), tight 1m tol, wake:  ~9.0 W  (duty cycle caps at 0.9)

References:
    Pahle, J. et al., "An Initial Flight Investigation of Formation Flight
        for Drag Reduction on the C-17 Aircraft," AIAA 2012-4802, 2012.
    Hanson, C.E. et al., "The DARPA/NASA Automated Airborne Refueling
        Demonstration," AIAA 2006-6610, 2006.

See docs/formation_flight/references.md for full citations.
"""

from wingz.mission.profiles import MissionProfile
from wingz.constants import N_SERVOS, SERVO_POWER_ACTIVE, SERVO_BASE_DUTY


def station_keeping_power(
    mission: MissionProfile,
    span_m: float,
    position_tolerance_m: float,
    is_leader: bool = False,
    in_wake: bool = True,
) -> float:
    """
    Estimate power (watts) for station-keeping servo actuation.

    Leader has zero cost. Followers pay for continuous control surface
    corrections against turbulence and wake vortex disturbances.
    Thrust adjustments are not modeled here -- trim thrust is already
    captured by the drag term (D*V).
    """
    if is_leader:
        return 0.0

    # Duty cycle scales with turbulence, tolerance, and wake effects
    turb_scale = mission.turbulence_intensity / 0.1   # normalized to light
    tol_scale = 2.0 / position_tolerance_m            # normalized to 2m
    wake_factor = 1.5 if in_wake else 1.0

    duty_cycle = min(SERVO_BASE_DUTY * turb_scale * tol_scale * wake_factor, 0.9)

    return N_SERVOS * SERVO_POWER_ACTIVE * duty_cycle
