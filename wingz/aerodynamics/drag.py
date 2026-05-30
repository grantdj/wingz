"""
Basic aerodynamic drag models.

References:
    Anderson, J.D., Fundamentals of Aerodynamics, 6th ed., McGraw-Hill, 2017.
    Prandtl, L., "Tragflügeltheorie," Nachrichten der Gesellschaft der
        Wissenschaften zu Göttingen, 1918. (Lifting-line theory)

See docs/formation_flight/references.md for full citations.
"""

import numpy as np
from wingz.mission.profiles import MissionProfile


def induced_drag(weight_N: float, span_m: float, mission: MissionProfile, formation_factor: float = 1.0) -> float:
    """
    D_i = W^2 / (q * pi * e * b^2)

    From Prandtl lifting-line theory for elliptically loaded wings.
    Ref: Anderson (2017) Eq. 5.63, 5.66.
    formation_factor < 1.0 reduces induced drag (wake surfing benefit).
    """
    q = mission.dynamic_pressure()
    return formation_factor * weight_N**2 / (q * np.pi * mission.oswald_e * span_m**2)


def parasite_drag(weight_N: float, mission: MissionProfile) -> float:
    """D_p = q * S * C_D0.  Ref: Anderson (2017) Ch. 5, Sec. 5.2."""
    q = mission.dynamic_pressure()
    area = mission.wing_area(weight_N)
    return q * area * mission.cd0


def total_drag(weight_N: float, span_m: float, mission: MissionProfile, formation_factor: float = 1.0) -> float:
    return induced_drag(weight_N, span_m, mission, formation_factor) + parasite_drag(weight_N, mission)
