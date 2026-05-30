"""
Formation aerodynamics based on Hummel/Lissaman classical wake interaction.

The key result: a trailing aircraft positioned in the upwash of a leader's
wingtip vortex sees reduced induced drag. The benefit depends on:
- Lateral overlap ratio (tip gap / span)
- Position in formation (leader gets nothing, first follower gets most)
- Formation geometry (V, echelon, inline)

We expose this as per-slot drag factors and an effective span for the whole formation.
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
    Based on Lissaman & Shollenberger (1970) and Hummel (1983).
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
    Effective span of the formation.
    b_eff = N * b / sqrt(sum(factor_i))
    """
    if N == 1:
        return span_m
    factors = per_slot_drag_factor(N, span_m, lateral_overlap_ratio, geometry)
    return N * span_m / np.sqrt(sum(factors))
