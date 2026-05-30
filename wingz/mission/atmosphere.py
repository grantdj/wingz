"""
International Standard Atmosphere (ISA) model.

Computes air properties as a function of altitude for troposphere (0-11km)
and lower stratosphere (11-20km).

References:
    ICAO Standard Atmosphere, ICAO Doc 7488/3, 1993.
    US Standard Atmosphere, 1976 (NASA-TM-X-74335).

See docs/formation_flight/references.md for full citations.
"""

from dataclasses import dataclass
import numpy as np
from wingz.mission.profiles import MissionProfile


# ISA constants
T0 = 288.15        # sea level temperature, K
P0 = 101325.0       # sea level pressure, Pa
RHO0 = 1.225        # sea level density, kg/m^3
LAPSE_RATE = 0.0065  # K/m in troposphere
TROPOPAUSE = 11000   # m
T_TROPOPAUSE = T0 - LAPSE_RATE * TROPOPAUSE  # ~216.65 K
G = 9.80665          # m/s^2
R = 287.058          # J/(kg·K), specific gas constant for dry air


@dataclass
class AtmosphereResult:
    altitude_m: float
    temperature_K: float
    pressure_Pa: float
    rho: float                   # kg/m^3
    turbulence_intensity: float  # 0-1 scale
    recommended_velocity: float  # m/s, cruise speed for solar aircraft


def standard_atmosphere(altitude_m: float) -> AtmosphereResult:
    """
    ISA model for troposphere and lower stratosphere.

    Troposphere (0-11km): linear temperature lapse, T = T0 - L*h
    Stratosphere (11-20km): isothermal at ~216.65 K
    """
    if altitude_m <= TROPOPAUSE:
        # Troposphere
        T = T0 - LAPSE_RATE * altitude_m
        P = P0 * (T / T0) ** (G / (LAPSE_RATE * R))
    else:
        # Lower stratosphere (isothermal)
        T = T_TROPOPAUSE
        # Pressure at tropopause
        P_trop = P0 * (T_TROPOPAUSE / T0) ** (G / (LAPSE_RATE * R))
        P = P_trop * np.exp(-G * (altitude_m - TROPOPAUSE) / (R * T_TROPOPAUSE))

    rho = P / (R * T)

    # Turbulence decreases with altitude — calm stratosphere
    # Exponential decay, normalized so sea level ~0.8, 20km ~0.1
    turbulence = 0.8 * np.exp(-altitude_m / 8000)

    # Recommended velocity for solar aircraft at altitude
    # Higher altitude = lower density = need more speed for same dynamic pressure
    # But solar aircraft are power-limited, so speed doesn't scale with 1/sqrt(rho)
    # Empirical: ~15 m/s at sea level analog, scaling gently with altitude
    # Typical HALE: 25 m/s at 20km, 35-40 m/s at 12km
    velocity = 15.0 + 10.0 * (altitude_m / 20000)  # simple linear, 15-25 m/s range

    return AtmosphereResult(
        altitude_m=altitude_m,
        temperature_K=T,
        pressure_Pa=P,
        rho=rho,
        turbulence_intensity=turbulence,
        recommended_velocity=velocity,
    )


def mission_at_altitude(
    altitude_m: float,
    oswald_e: float = 0.85,
    cd0: float = 0.025,
    wing_loading_N_m2: float = 45.0,
    min_endurance_days: int = 30,
) -> MissionProfile:
    """Create a MissionProfile at any altitude using the atmosphere model."""
    atm = standard_atmosphere(altitude_m)
    return MissionProfile(
        name=f"Alt {altitude_m/1000:.0f}km",
        altitude_m=altitude_m,
        rho=atm.rho,
        velocity=atm.recommended_velocity,
        oswald_e=oswald_e,
        cd0=cd0,
        wing_loading_N_m2=wing_loading_N_m2,
        min_endurance_days=min_endurance_days,
        turbulence_intensity=atm.turbulence_intensity,
    )
