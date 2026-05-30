"""
Cost model using mass as a proxy. Avoids dollar values entirely.

cost = (w_s * m_struct + w_c * m_ctrl) * N^alpha

No published source — project-specific proxy. Per-unit cost data for
solar HALE platforms is unavailable; mass serves as a reasonable proxy
since heavier = more material = more expensive, and control hardware
is more expensive per kg than airframe structure.

See docs/formation_flight/references.md for discussion.
"""


def mass_proxy_cost(
    structural_mass_kg: float,
    control_mass_kg: float,
    N: int,
    structural_weight: float = 1.0,
    control_weight: float = 2.0,
    complexity_exponent: float = 1.2,
) -> float:
    mass_score = structural_weight * structural_mass_kg + control_weight * control_mass_kg
    complexity_score = N ** complexity_exponent if N > 1 else 1.0
    return mass_score * complexity_score
