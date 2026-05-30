from dataclasses import dataclass


@dataclass
class MissionProfile:
    name: str
    altitude_m: float
    rho: float                    # kg/m^3, air density at altitude
    velocity: float               # m/s, cruise speed
    oswald_e: float               # span efficiency factor
    cd0: float                    # parasite drag coefficient
    wing_loading_N_m2: float      # W/S, N/m^2
    min_endurance_days: int        # minimum mission duration
    turbulence_intensity: float   # relative scale 0-1 (0=calm, 1=severe)

    def dynamic_pressure(self) -> float:
        return 0.5 * self.rho * self.velocity**2

    def wing_area(self, weight_N: float) -> float:
        return weight_N / self.wing_loading_N_m2


def hale_20km() -> MissionProfile:
    return MissionProfile(
        name="HALE 20km",
        altitude_m=20000,
        rho=0.0889,
        velocity=25.0,
        oswald_e=0.85,
        cd0=0.025,
        wing_loading_N_m2=45.0,
        min_endurance_days=30,
        turbulence_intensity=0.1,
    )


def lower_altitude_le() -> MissionProfile:
    return MissionProfile(
        name="Lower-altitude LE",
        altitude_m=12000,
        rho=0.312,
        velocity=40.0,
        oswald_e=0.82,
        cd0=0.028,
        wing_loading_N_m2=80.0,
        min_endurance_days=30,
        turbulence_intensity=0.4,
    )
