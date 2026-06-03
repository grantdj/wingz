"""
Parametric aircraft geometry — fully continuous design space.

Every configuration (flying wing, twin-boom, tandem, joined wing, box wing,
canard, strut-braced) is reachable by varying continuous parameters.
No discrete config types — the optimizer interpolates freely.

Design variables (~30):
    Wing:      span, AR, taper, sweep, dihedral break
    Fuselage:  length, diameter (constrained by payload bay)
    Tail:      boom length, h-tail area, v-tail area (0 = tailless)
    2nd wing:  area fraction, x-offset, z-offset, span fraction, tip-join
    Strut:     presence (continuous), span station, diameter
    Structure: spar OD/wall root/tip, rib spacing, skin density
"""

from dataclasses import dataclass, field
import numpy as np


@dataclass
class PayloadBay:
    """Minimum volume the fuselage must enclose."""
    length_m: float = 0.4
    diameter_m: float = 0.15
    mass_kg: float = 5.0
    power_W: float = 50.0


@dataclass
class AircraftGeometry:
    """Fully parametric aircraft geometry. All floats, all continuous."""

    # ── Primary wing ──────────────────────────────────────────────
    span: float = 20.0            # m, full span
    aspect_ratio: float = 12.0
    taper_ratio: float = 0.6      # tip_chord / root_chord
    sweep_deg: float = 0.0        # quarter-chord sweep (degrees)
    dihedral_deg: float = 2.0     # inboard dihedral (degrees)
    dihedral_break: float = 0.5   # span fraction where break occurs
    dihedral_break_angle: float = 0.0  # additional outboard dihedral (degrees)

    # ── Fuselage ──────────────────────────────────────────────────
    fuselage_length: float = 1.0  # m
    fuselage_diameter: float = 0.20  # m
    fuselage_x_offset: float = 0.0  # m, fwd/aft of wing LE

    # ── Tail / empennage ──────────────────────────────────────────
    boom_length: float = 2.0      # m, 0 = tailless (flying wing)
    boom_diameter: float = 0.03   # m
    h_tail_area_frac: float = 0.10  # as fraction of wing area
    v_tail_area_frac: float = 0.05  # as fraction of wing area
    tail_aspect_ratio: float = 4.0

    # ── Second lifting surface ────────────────────────────────────
    # 0 area = no second wing. Positive x_offset = aft (tandem).
    # Negative x_offset = forward (canard).
    # Nonzero z_offset + join > 0.5 = box/joined wing.
    wing2_area_frac: float = 0.0    # fraction of primary wing area
    wing2_x_offset: float = 2.0     # m, from primary wing LE
    wing2_z_offset: float = 0.0     # m, vertical offset
    wing2_span_frac: float = 0.6    # span as fraction of primary
    wing2_taper: float = 0.7
    wing2_join: float = 0.0         # 0-1, >0.5 = tips connected (box wing)

    # ── Strut ─────────────────────────────────────────────────────
    strut_factor: float = 0.0     # 0-1, >0.5 = strut present
    strut_span_frac: float = 0.5  # where strut meets wing
    strut_diameter: float = 0.02  # m

    # ── Structure (spar design variables) ─────────────────────────
    spar_od_root: float = 0.06
    spar_od_tip: float = 0.03
    spar_wall_root: float = 1.5e-3
    spar_wall_tip: float = 0.5e-3
    rib_spacing: float = 0.4
    skin_density: float = 0.20    # kg/m², wing covering

    # ── Propulsion ────────────────────────────────────────────────
    n_motors: float = 1.0         # rounded to int in analysis
    motor_span_frac: float = 0.0  # for outboard motors

    @property
    def root_chord(self) -> float:
        wing_area = self.span**2 / self.aspect_ratio
        return 2 * wing_area / (self.span * (1 + self.taper_ratio))

    @property
    def tip_chord(self) -> float:
        return self.root_chord * self.taper_ratio

    @property
    def wing_area(self) -> float:
        return self.span**2 / self.aspect_ratio

    @property
    def half_span(self) -> float:
        return self.span / 2.0

    @property
    def has_tail(self) -> bool:
        return self.boom_length > 0.3 and (self.h_tail_area_frac > 0.01
                                            or self.v_tail_area_frac > 0.01)

    @property
    def has_second_wing(self) -> bool:
        return self.wing2_area_frac > 0.02

    @property
    def has_strut(self) -> bool:
        return self.strut_factor > 0.5

    @property
    def is_joined(self) -> bool:
        return self.has_second_wing and self.wing2_join > 0.5

    @property
    def wing2_area(self) -> float:
        return self.wing_area * self.wing2_area_frac

    @property
    def wing2_span(self) -> float:
        return self.span * self.wing2_span_frac

    @property
    def h_tail_area(self) -> float:
        return self.wing_area * self.h_tail_area_frac

    @property
    def v_tail_area(self) -> float:
        return self.wing_area * self.v_tail_area_frac

    @property
    def total_lifting_area(self) -> float:
        """Total area of all lifting surfaces (for solar panel placement)."""
        area = self.wing_area
        if self.has_second_wing:
            area += self.wing2_area
        if self.has_tail:
            area += self.h_tail_area
        return area

    @property
    def solar_area(self) -> float:
        """Area available for solar panels (upper surface of lifting surfaces)."""
        return self.total_lifting_area


def enforce_payload_constraint(geo: AircraftGeometry, bay: PayloadBay) -> AircraftGeometry:
    """Ensure fuselage is at least large enough for the payload bay."""
    geo.fuselage_length = max(geo.fuselage_length, bay.length_m * 1.1)
    geo.fuselage_diameter = max(geo.fuselage_diameter, bay.diameter_m * 1.1)
    return geo


# ── Design variable packing / unpacking ─────────────────────────────

DESIGN_VAR_NAMES = [
    'span', 'aspect_ratio', 'taper_ratio', 'sweep_deg',
    'dihedral_deg', 'dihedral_break', 'dihedral_break_angle',
    'fuselage_length', 'fuselage_diameter',
    'boom_length', 'h_tail_area_frac', 'v_tail_area_frac', 'tail_aspect_ratio',
    'wing2_area_frac', 'wing2_x_offset', 'wing2_z_offset',
    'wing2_span_frac', 'wing2_taper', 'wing2_join',
    'strut_factor', 'strut_span_frac',
    'spar_od_root', 'spar_od_tip', 'spar_wall_root', 'spar_wall_tip',
    'rib_spacing', 'skin_density',
    'n_motors',
]

N_DESIGN_VARS = len(DESIGN_VAR_NAMES)


def default_bounds(bay: PayloadBay) -> list[tuple[float, float]]:
    """Bounds for each design variable. Order matches DESIGN_VAR_NAMES."""
    return [
        (8.0,  40.0),           # span
        (6.0,  25.0),           # aspect_ratio
        (0.3,  1.0),            # taper_ratio
        (-5.0, 15.0),           # sweep_deg
        (0.0,  8.0),            # dihedral_deg
        (0.3,  0.7),            # dihedral_break
        (0.0,  15.0),           # dihedral_break_angle
        (bay.length_m, 3.0),    # fuselage_length
        (bay.diameter_m, 0.5),  # fuselage_diameter
        (0.0,  5.0),            # boom_length (0 = tailless)
        (0.0,  0.15),           # h_tail_area_frac
        (0.0,  0.08),           # v_tail_area_frac
        (3.0,  6.0),            # tail_aspect_ratio
        (0.0,  0.5),            # wing2_area_frac (0 = single wing)
        (-3.0, 5.0),            # wing2_x_offset
        (0.0,  3.0),            # wing2_z_offset
        (0.3,  1.0),            # wing2_span_frac
        (0.4,  1.0),            # wing2_taper
        (0.0,  1.0),            # wing2_join
        (0.0,  1.0),            # strut_factor
        (0.3,  0.7),            # strut_span_frac
        (0.01, 0.15),           # spar_od_root
        (0.005, 0.10),          # spar_od_tip
        (0.3e-3, 5e-3),         # spar_wall_root
        (0.3e-3, 3e-3),         # spar_wall_tip
        (0.15, 1.0),            # rib_spacing
        (0.10, 0.40),           # skin_density
        (1.0,  4.0),            # n_motors
    ]


def unpack(x: np.ndarray) -> AircraftGeometry:
    """Convert optimizer vector to AircraftGeometry."""
    geo = AircraftGeometry()
    for i, name in enumerate(DESIGN_VAR_NAMES):
        setattr(geo, name, float(x[i]))
    return geo


def pack(geo: AircraftGeometry) -> np.ndarray:
    """Convert AircraftGeometry to optimizer vector."""
    return np.array([getattr(geo, name) for name in DESIGN_VAR_NAMES])
