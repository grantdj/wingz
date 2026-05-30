"""
Empirical wing mass scaling for solar/HALE aircraft.

Two models:
1. Power-law fit m_wing = a * b^n — calibrated to real aircraft data, span-only.
2. AR-corrected model — adds a physics-based penalty for high aspect ratio
   based on spar sizing constraints.

The AR correction comes from beam bending: the spar moment of inertia I is
limited by the available spar depth, which is constrained by chord and airfoil
thickness ratio:

    chord = span / AR
    max_spar_depth = chord * (t/c)
    I ~ cap_area * (depth/2)^2

For the same bending moment, a shallower spar needs more cap area (and mass)
to achieve the same I. The penalty scales as:

    m_corrected = m_base * (AR / AR_ref)^ar_exponent

where AR_ref is the typical AR of the calibration aircraft (~25) and
ar_exponent captures how fast structural mass grows with AR. From beam
theory, I ~ depth^2 and depth ~ 1/AR, so cap_area ~ AR^2 for constant I.
In practice the exponent is lower (~1.0-1.5) because designers trade off
deflection limits, use higher-grade materials, and accept more flexibility
at high AR.

References:
    Raymer, D.P., Aircraft Design: A Conceptual Approach, 6th ed., AIAA, 2018.
        Ch. 15, Eq. 15.1-15.5. (Wing weight estimation methods)
    Torenbeek, E., Synthesis of Subsonic Airplane Design, Springer, 1982.
        Ch. 8. (Cantilever wing scaling)
    Roskam, J., Airplane Design, Part V, DAR Corporation, 1999.
        (Component weight estimation)

The fitted exponent (~2.4) exceeds 2.0 due to stiffness-limited design at
large spans. Euler-Bernoulli beam theory: delta = FL^3/(3EI) — deflection
grows with span^3, requiring progressively heavier spars.

See docs/formation_flight/references.md for full citations and data sources.
"""

from dataclasses import dataclass
import numpy as np
from scipy.optimize import curve_fit


SOLAR_HALE_DATA = [
    {"name": "Zephyr S", "span_m": 25, "wing_mass_kg": 7, "mtow_kg": 75,
     "source": "Airbus", "mass_confidence": "estimated"},
    {"name": "PHASA-35", "span_m": 35, "wing_mass_kg": 15, "mtow_kg": 150,
     "source": "BAE Systems", "mass_confidence": "estimated"},
    {"name": "Pathfinder Plus", "span_m": 36.3, "wing_mass_kg": 30, "mtow_kg": 315,
     "source": "NASA", "mass_confidence": "estimated"},
    {"name": "Odysseus", "span_m": 74, "wing_mass_kg": 130, "mtow_kg": 180,
     "source": "Boeing Aurora", "mass_confidence": "estimated"},
    {"name": "Helios", "span_m": 75.3, "wing_mass_kg": 180, "mtow_kg": 1052,
     "source": "NASA", "mass_confidence": "estimated"},
    {"name": "HAPSMobile Sunglider", "span_m": 78, "wing_mass_kg": 200, "mtow_kg": 260,
     "source": "SoftBank", "mass_confidence": "estimated"},
    {"name": "Solar Impulse 2", "span_m": 71.9, "wing_mass_kg": 250, "mtow_kg": 2300,
     "source": "SI Foundation", "mass_confidence": "estimated"},
]


def _power_law(span, coefficient, exponent):
    return coefficient * span**exponent


def fit_power_law(data: list[dict]) -> tuple[float, float]:
    spans = np.array([d["span_m"] for d in data])
    masses = np.array([d["wing_mass_kg"] for d in data])
    popt, _ = curve_fit(_power_law, spans, masses, p0=[0.01, 2.0])
    return float(popt[0]), float(popt[1])


@dataclass
class EmpiricalStructure:
    coefficient: float
    exponent: float
    min_span: float
    max_span: float
    ar_ref: float = 25.0        # reference AR of calibration aircraft
    ar_exponent: float = 1.2    # structural mass penalty exponent for AR > ar_ref

    @classmethod
    def from_data(cls, data: list[dict], ar_ref: float = 25.0,
                  ar_exponent: float = 1.2) -> "EmpiricalStructure":
        coefficient, exponent = fit_power_law(data)
        spans = [d["span_m"] for d in data]
        return cls(coefficient=coefficient, exponent=exponent,
                   min_span=min(spans), max_span=max(spans),
                   ar_ref=ar_ref, ar_exponent=ar_exponent)

    def wing_mass(self, span_m: float, aspect_ratio: float | None = None) -> float:
        """
        Wing structural mass.

        If aspect_ratio is provided, applies an AR correction:
            m = m_base * (AR / AR_ref) ^ ar_exponent

        The correction is > 1.0 for AR > AR_ref (thinner chord, shallower spar,
        needs more cap area) and < 1.0 for AR < AR_ref (deeper spar, lighter caps).

        Physics: spar depth ~ chord * t/c = span/(AR) * t/c
        For constant bending stiffness I, cap_area ~ 1/depth^2 ~ AR^2.
        The ar_exponent of 1.2 is conservative (less than the theoretical 2.0)
        because real designs trade off deflection limits and accept more
        flexibility at high AR. This should be replaced by the beam model
        for quantitative results.

        Ref: Euler-Bernoulli beam, I = A * (d/2)^2. Raymer Ch. 15.
        """
        base = self.coefficient * span_m**self.exponent
        if aspect_ratio is None or aspect_ratio == self.ar_ref:
            return base
        return base * (aspect_ratio / self.ar_ref) ** self.ar_exponent

    def wing_mass_with_confidence(self, span_m: float,
                                  aspect_ratio: float | None = None) -> dict:
        return {
            "mass_kg": self.wing_mass(span_m, aspect_ratio),
            "interpolating": self.min_span <= span_m <= self.max_span,
        }
