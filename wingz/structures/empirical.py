"""
Empirical wing mass scaling for solar/HALE aircraft.

Power-law fit m_wing = a * b^n calibrated to real aircraft data.

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

    @classmethod
    def from_data(cls, data: list[dict]) -> "EmpiricalStructure":
        coefficient, exponent = fit_power_law(data)
        spans = [d["span_m"] for d in data]
        return cls(coefficient=coefficient, exponent=exponent, min_span=min(spans), max_span=max(spans))

    def wing_mass(self, span_m: float) -> float:
        return self.coefficient * span_m**self.exponent

    def wing_mass_with_confidence(self, span_m: float) -> dict:
        return {"mass_kg": self.wing_mass(span_m), "interpolating": self.min_span <= span_m <= self.max_span}
