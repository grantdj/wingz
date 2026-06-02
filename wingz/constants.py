"""
Shared physical and design constants for the wingz formation flight model.

Every magic number in the codebase should trace back here. If a script
or module uses a numeric literal for any of these quantities, it's a bug.

To change a parameter globally, change it here. All scripts and the sweep
engine import from this module.

Constants are organized as:
  - Physical constants (immutable physics)
  - Default design parameters (unlockable for optimization)
  - Derived quantities and notes
"""

# ═══════════════════════════════════════════════════════════════════════════
# PHYSICAL CONSTANTS — these don't change
# ═══════════════════════════════════════════════════════════════════════════

GRAVITY = 9.81                    # m/s²
SOLAR_CONSTANT = 1361.0           # W/m², total solar irradiance at 1 AU (ASTM E490)

# ═══════════════════════════════════════════════════════════════════════════
# DESIGN PARAMETERS — defaults for the solver, all unlockable for search
# ═══════════════════════════════════════════════════════════════════════════

# ── Atmosphere ────────────────────────────────────────────────────────────
CRUISE_ALTITUDE_M = 20000         # nominal cruise altitude (m)
RHO_20KM = 0.0889                # air density at 20 km (kg/m³)

# ── Aerodynamics ──────────────────────────────────────────────────────────
CL_MAX = 1.2                     # max lift coefficient (thin high-altitude airfoil)
#   Depends on Re (chord × speed × rho / mu). At Re < 200k, CL_max drops.
#   Unlock range: 0.8–1.4

OSWALD_E = 0.85                  # Oswald span efficiency factor
#   Varies with AR and planform shape. Higher AR → slightly lower e.
#   Unlock range: 0.75–0.90

CD0 = 0.025                      # zero-lift drag coefficient (wing only)
#   Flying wing: ~0.020 (no fuselage)
#   Boom-tail (Zephyr-style): ~0.028
#   Conventional (fuselage + tail): ~0.035
#   Unlock range: 0.018–0.040

AIRFOIL_THICKNESS_RATIO = 0.14   # t/c, typical for HALE airfoils (14%)
#   Thicker at low Re might improve CL_max. Thinner reduces profile drag.
#   Unlock range: 0.10–0.18

# ── Speed margins ─────────────────────────────────────────────────────────
STALL_MARGIN_DAY = 1.15           # V_cruise / V_stall during daytime
STALL_MARGIN_NIGHT = 1.03         # V_cruise / V_stall at night (calm stratosphere)
#   Day: convective thermals, gusts 1–3 m/s → need margin
#   Night: radiative cooling, near-zero turbulence → fly close to stall
#   Unlock range: day 1.05–1.30, night 1.01–1.15

# ── Solar ─────────────────────────────────────────────────────────────────
PANEL_EFFICIENCY = 0.30           # MicroLink III-V ELO production (28-31%), Zephyr/PHASA-35
#   Si (SunPower Maxeon, Skydweller): 0.22–0.24
#   GaAs single-junction (Alta, defunct): 0.26–0.29
#   III-V triple-junction production: 0.28–0.31
#   III-V triple-junction lab record: 0.3775 (MicroLink, 2018)
#   Perovskite/III-V tandem (future): 0.33–0.35
#   Unlock range: 0.22–0.38

SOLAR_POWER_MARGIN = 3.0         # panel area sized to produce margin × total power required
#   Replaces fixed PANEL_COVERAGE. Coverage is computed as:
#   coverage = min(power_required * 24h * margin / available_solar, MAX_PANEL_COVERAGE)
#   At 3.0×, panels collect 3× what's needed over 24h, ensuring battery
#   charges well before sunset with margin for clouds/seasons.

MAX_PANEL_COVERAGE = 0.90        # maximum fraction of wing that can have panels
#   Limited by: ailerons, spar caps, structural joints, wing root
#   Flying wing: up to 0.92. Boom-tail: ~0.85–0.90. Conventional: ~0.80.

PANEL_AREAL_DENSITY = 0.5        # kg/m², installed III-V ELO solar panel
#   MicroLink cell: ~0.15 kg/m² (bare cell, >3000 W/kg)
#   Encapsulation + wiring + interconnects: ~0.2 kg/m²
#   Mounting/bonding to wing skin: ~0.15 kg/m²
#   Total installed: ~0.5 kg/m² (~1500 W/kg at panel level)
#   Unlock range: 0.3–0.8

# ── Propulsion ────────────────────────────────────────────────────────────
PROPULSION_EFFICIENCY = 0.75      # combined propeller × motor × ESC efficiency
#   Motor: 90–93%, Propeller: 80–85%, ESC: 95–98% → total ~0.70–0.78
#   Varies with power level and speed. Lower at very low power.
#   Unlock range: 0.65–0.85

# ── Battery ───────────────────────────────────────────────────────────────
BATTERY_ENERGY_DENSITY = 250.0    # Wh/kg, current Li-ion (cell level)
#   Li-ion (current): 250 Wh/kg
#   Li-S (near-term): 400 Wh/kg
#   Solid state (future): 500+ Wh/kg
#   Aerospace pack derate: ~10% for BMS, wiring, enclosure
#   Unlock range: 200–500

# ── Structure ─────────────────────────────────────────────────────────────
CFRP_DENSITY = 1550               # kg/m³, carbon fiber composite density
STRUCTURAL_LOAD_FACTOR = 1.2      # design gust load factor (stratospheric HALE)
#   Unlock range: 1.0–2.0 (1.0 = benign stratosphere, 2.0 = conservative)

SKIN_AREAL_DENSITY = 0.3          # kg/m², wing covering (film + ribs, not solid CFRP)
#   Lighter covering → lighter wing but less torsional stiffness
#   Unlock range: 0.15–0.50

SIGMA_ALLOWABLE = 800e6           # Pa, spar cap allowable stress (compression w/ 1.5 SF)
#   Higher-grade CF could allow more. Lower SF for benign loads.
#   Unlock range: 600e6–1200e6

# ── Control hardware ──────────────────────────────────────────────────────
HARDWARE_MASS_LEADER = 2.5        # kg, full nav suite (IMU + GPS + comms + compute)
HARDWARE_MASS_FOLLOWER = 0.4      # kg, relative nav (UWB/visual + datalink)
HARDWARE_POWER_LEADER = 15.0      # W
HARDWARE_POWER_FOLLOWER = 3.0     # W

# ── Station keeping ───────────────────────────────────────────────────────
N_SERVOS = 4                      # aileron ×2, elevator, rudder
SERVO_POWER_ACTIVE = 2.5          # W per servo when correcting
SERVO_BASE_DUTY = 0.25            # baseline duty cycle (light turbulence, 2m tolerance)

# ── Formation geometry ────────────────────────────────────────────────────
DEFAULT_OVERLAP_RATIO = 0.1       # lateral wingtip overlap (optimal per Hummel/Lissaman)
POSITION_TOLERANCE_M = 2.0        # station-keeping tolerance (m)

# ── Payload ───────────────────────────────────────────────────────────────
PAYLOAD_SPECIFIC_MASS = 50        # g/W, typical payload mass per watt of power
#   EO/IR gimbal: 80–120 g/W
#   Comms relay: 30–50 g/W
#   Software-defined radio: 30–40 g/W
#   Edge compute (Jetson): 15–20 g/W
#   Unlock range: 15–120

# ── Night operations ──────────────────────────────────────────────────────
NIGHT_DESCENT_M = 0.0             # altitude traded during night (m), 0 = level flight
CLIMB_POWER_FRACTION = 0.80       # fraction of daytime excess power used for climbing
#   Remaining goes to battery charging

# ── Mission ───────────────────────────────────────────────────────────────
DEFAULT_LATITUDE = 30.0           # degrees N
DEFAULT_DAY_OF_YEAR = 172         # ~summer solstice
MIN_ENDURANCE_DAYS = 30           # mission duration target

# ── Cost ──────────────────────────────────────────────────────────────────
DEFAULT_PRODUCTION_RUN = 10       # fleets built (for capital amortization)
