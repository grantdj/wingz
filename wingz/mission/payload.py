"""
Payload definitions for solar HALE aircraft.

Payload contributes mass and power draw. In formation architectures,
payload can be distributed across aircraft or concentrated on specific
vehicles (e.g., only the navigator carries the full sensor suite).
"""

from dataclasses import dataclass


@dataclass
class Payload:
    name: str
    mass_kg: float = 0.0
    power_W: float = 0.0


def no_payload() -> Payload:
    """Zero payload — structure and control only."""
    return Payload(name="none", mass_kg=0.0, power_W=0.0)


def surveillance_payload() -> Payload:
    """Typical EO/IR surveillance sensor package."""
    return Payload(name="surveillance", mass_kg=8.0, power_W=50.0)


def comms_relay_payload() -> Payload:
    """Communications relay package."""
    return Payload(name="comms_relay", mass_kg=12.0, power_W=100.0)


def scientific_payload() -> Payload:
    """Atmospheric science instruments."""
    return Payload(name="scientific", mass_kg=5.0, power_W=30.0)
