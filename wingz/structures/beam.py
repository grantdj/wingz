"""
Analytical beam model for wing structural sizing.

Sizes the wing spar from the actual loaded aircraft weight using
Euler-Bernoulli beam theory. This replaces the empirical power-law
model when the aircraft is loaded significantly beyond the weight
range of the calibration data.

The wing structure consists of:
- Spar caps (top/bottom, carry bending loads)
- Spar web (carries shear)
- Skin (aerodynamic surface, carries torsion)

The spar depth is constrained by the airfoil thickness:
    spar_depth = chord * (t/c)
    chord = span / AR

For a given bending moment, the required spar cap area is:
    A_cap = M_root / (sigma_allowable * spar_depth)

This creates the fundamental AR penalty: thinner chord → shallower spar →
more cap area → heavier structure.

References:
    Euler-Bernoulli beam: delta = FL^3 / (3EI)
    Raymer, Aircraft Design, Ch. 15 (wing weight estimation)
    Torenbeek, Synthesis of Subsonic Airplane Design, Ch. 8
    Noth, Design of Solar Powered Airplanes, ETH Zurich, 2008
        (solar HALE structural sizing)

See docs/formation_flight/references.md for full citations.
"""

from dataclasses import dataclass
import numpy as np

from wingz.constants import (
    CFRP_DENSITY, AIRFOIL_THICKNESS_RATIO, STRUCTURAL_LOAD_FACTOR,
    SKIN_AREAL_DENSITY,
)


@dataclass
class BeamStructure:
    """Analytical wing structure model based on beam theory."""

    # Material properties
    sigma_allowable: float = 800e6  # Pa (compression with 1.5 SF)
    E: float = 135e9                # Pa, Young's modulus
    rho_material: float = CFRP_DENSITY

    # Airfoil geometry
    thickness_ratio: float = AIRFOIL_THICKNESS_RATIO

    # Design loads
    load_factor: float = STRUCTURAL_LOAD_FACTOR

    # Mass estimation factors
    web_fraction: float = 0.30      # web mass as fraction of cap mass
    skin_areal_density: float = SKIN_AREAL_DENSITY

    def wing_mass(
        self,
        span_m: float,
        aspect_ratio: float,
        total_aircraft_mass_kg: float,
    ) -> float:
        """
        Compute wing structural mass from loaded aircraft weight.

        This is the key function: structure is sized to carry the ACTUAL
        aircraft weight, not an empirical estimate from empty aircraft.

        Returns total wing mass in kg (both halves).
        """
        chord = span_m / aspect_ratio
        spar_depth = chord * self.thickness_ratio
        half_span = span_m / 2

        # Design load
        W = total_aircraft_mass_kg * 9.81 * self.load_factor

        # Root bending moment (elliptic lift distribution)
        # M = W * b / (3*pi) for true elliptic; simplified to W*L/8
        M_root = W * half_span / 8

        # Required spar cap area
        A_cap = M_root / (self.sigma_allowable * spar_depth)

        # Spar cap mass (2 caps × half span × area × density) × 2 halves
        cap_mass = 2 * A_cap * half_span * self.rho_material

        # Spar web
        web_mass = cap_mass * self.web_fraction

        # Wing covering (film + ribs, not solid CFRP skin)
        # Solar HALE wings use film covering or solar cells as skin,
        # not structural CFRP panels. Areal density ~0.3 kg/m².
        wing_area = span_m * chord
        covering_mass = wing_area * self.skin_areal_density

        return cap_mass + web_mass + covering_mass

    def tip_deflection(
        self,
        span_m: float,
        aspect_ratio: float,
        total_aircraft_mass_kg: float,
    ) -> float:
        """Wingtip deflection under design load (meters)."""
        chord = span_m / aspect_ratio
        spar_depth = chord * self.thickness_ratio
        half_span = span_m / 2

        W = total_aircraft_mass_kg * 9.81 * self.load_factor
        M_root = W * half_span / 8
        A_cap = M_root / (self.sigma_allowable * spar_depth)
        I = A_cap * spar_depth**2 / 2

        if I <= 0:
            return float('inf')

        return W * half_span**3 / (3 * self.E * I)

    def deflection_percent(
        self,
        span_m: float,
        aspect_ratio: float,
        total_aircraft_mass_kg: float,
    ) -> float:
        """Tip deflection as percentage of half-span."""
        defl = self.tip_deflection(span_m, aspect_ratio, total_aircraft_mass_kg)
        return defl / (span_m / 2) * 100
