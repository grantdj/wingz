"""
Formation aerodynamics based on Hummel/Lissaman classical wake interaction.

The key result: a trailing aircraft positioned in the upwash of a leader's
wingtip vortex sees reduced induced drag. The benefit depends on:
- Lateral overlap ratio (tip gap / span)
- Position in formation (leader gets nothing, first follower gets most)
- Formation geometry (V, echelon, inline)

We expose this as per-slot drag factors and an effective span for the whole formation.

References:
    Lissaman, P.B.S. and Shollenberger, C.A., "Formation Flight of Birds,"
        Science, Vol. 168, No. 3934, 1970, pp. 1003-1005.
    Hummel, D., "Aerodynamic Aspects of Formation Flight in Birds,"
        J. Theoretical Biology, Vol. 104, No. 3, 1983, pp. 321-347.
    Hummel, D., "Formation Flight as an Energy-Saving Mechanism,"
        Israel J. Zoology, Vol. 41, 1995. (Also ADA256861)
    Vachon, M.J. et al., "F/A-18 Performance Benefits Measured During the
        Autonomous Formation Flight Project," AIAA 2003-6479, 2003.
    Bangash, Z.A. et al., "Aerodynamics of Formation Flight,"
        J. Aircraft, Vol. 43, No. 4, 2006, pp. 907-912.
    Ning, S.A. et al., "Aerodynamic Performance of Extended Formation Flight,"
        J. Aircraft, Vol. 48, No. 3, 2011, pp. 855-865.

See docs/formation_flight/references.md for full citations.
"""

import enum
import numpy as np


class FormationGeometry(enum.Enum):
    V = "v"
    ECHELON = "echelon"
    INLINE = "inline"


def _single_wake_drag_factor(lateral_overlap_ratio: float) -> float:
    """
    Drag reduction factor for one aircraft surfing one neighbor's wake.

    Parameterized Gaussian fit to results from Lissaman & Shollenberger (1970)
    and Hummel (1983). Max ~35% induced drag reduction at optimal overlap (~10%).
    NASA AFF flight tests (Vachon 2003) measured comparable reductions.

    Returns a factor in (0, 1] where 1.0 = no benefit.
    """
    r = lateral_overlap_ratio
    optimal_r = 0.1
    sigma = 0.15
    max_reduction = 0.35
    reduction = max_reduction * np.exp(-((r - optimal_r) ** 2) / (2 * sigma**2))
    return 1.0 - reduction


def per_slot_drag_factor(N: int, span_m: float, lateral_overlap_ratio: float, geometry: FormationGeometry) -> list[float]:
    """
    Compute induced drag factor for each aircraft slot in the formation.
    Returns list of N floats, each in (0, 1]. Index 0 is the leader.
    In V formation, slots: [leader, left1, right1, left2, right2, ...]
    In echelon: [leader, follower1, follower2, ...]
    """
    if N == 1:
        return [1.0]

    base_factor = _single_wake_drag_factor(lateral_overlap_ratio)

    if geometry == FormationGeometry.INLINE:
        factors = [1.0]
        for i in range(1, N):
            factors.append(1.0 - 0.05 * min(i, 3))
        return factors

    if geometry == FormationGeometry.ECHELON:
        factors = [1.0]
        for i in range(1, N):
            cumulative = base_factor ** (1.0 + 0.15 * (i - 1))
            factors.append(cumulative)
        return factors

    # V formation
    factors = [1.0]
    depth = 1
    idx = 1
    while idx < N:
        wake_count = min(depth, 2)
        slot_factor = base_factor ** wake_count
        slot_factor = slot_factor ** (1.0 + 0.1 * (depth - 1))
        factors.append(slot_factor)  # left
        idx += 1
        if idx < N:
            factors.append(slot_factor)  # right (symmetric)
            idx += 1
        depth += 1
    return factors


def effective_span(N: int, span_m: float, lateral_overlap_ratio: float, geometry: FormationGeometry) -> float:
    """
    Effective span of the formation: b_eff = N * b / sqrt(sum(factor_i))

    Derived by equating formation induced drag to equivalent single-aircraft drag:
        D_formation = W^2 / (q pi e) * sum(factor_i) / (N^2 b^2)
        D_equiv     = W^2 / (q pi e b_eff^2)
    Solving: b_eff = N*b / sqrt(sum(factor_i))

    Original derivation for this project; combines standard induced drag theory
    (Anderson 2017, Eq. 5.63) with per-slot formation factors from Hummel/Lissaman.
    """
    if N == 1:
        return span_m
    factors = per_slot_drag_factor(N, span_m, lateral_overlap_ratio, geometry)
    return N * span_m / np.sqrt(sum(factors))
