"""
Shared physical and design constants for the wingz formation flight model.

Every magic number in the codebase should trace back here. If a script
or module uses a numeric literal for any of these quantities, it's a bug.

To change a parameter globally, change it here. All scripts and the sweep
engine import from this module.
"""

# ── Atmosphere ────────────────────────────────────────────────────────────
CRUISE_ALTITUDE_M = 20000         # nominal cruise altitude (m)
RHO_20KM = 0.0889                # air density at 20 km (kg/m³)
GRAVITY = 9.81                    # m/s²

# ── Aerodynamics ──────────────────────────────────────────────────────────
CL_MAX = 1.2                     # max lift coefficient (thin high-altitude airfoil)
OSWALD_E = 0.85                  # Oswald span efficiency factor
CD0 = 0.025                      # zero-lift drag coefficient (wing only)
#   Boom-tail aircraft: ~0.028
#   Conventional (fuselage + tail): ~0.035

# ── Speed margins ─────────────────────────────────────────────────────────
STALL_MARGIN_DAY = 1.15           # V_cruise / V_stall during daytime
STALL_MARGIN_NIGHT = 1.03         # V_cruise / V_stall at night (calm stratosphere)
#   Day: convective thermals, occasional gusts 1-3 m/s → need margin
#   Night: radiative cooling, near-zero turbulence → fly close to stall

# ── Solar ─────────────────────────────────────────────────────────────────
SOLAR_CONSTANT = 1361.0           # W/m², total solar irradiance at 1 AU (ASTM E490)
PANEL_EFFICIENCY = 0.38           # MicroLink III-V ELO, flight-proven on Zephyr/PHASA-35
PANEL_COVERAGE = 0.80             # fraction of wing area covered by solar cells
#   Remaining 20%: ailerons, spar caps, structural joints, wing root

# ── Propulsion ────────────────────────────────────────────────────────────
PROPULSION_EFFICIENCY = 0.75      # combined propeller × motor × ESC efficiency
#   Motor: 90-93%, Propeller: 80-85%, ESC: 95-98% → total ~0.70-0.78

# ── Battery ───────────────────────────────────────────────────────────────
BATTERY_ENERGY_DENSITY = 250.0    # Wh/kg, current Li-ion (cell level)
#   Aerospace-qualified pack: derate ~10% for BMS, wiring, enclosure
#   Li-S (near-term): ~400 Wh/kg
#   Solid state (future): ~500+ Wh/kg

# ── Structure ─────────────────────────────────────────────────────────────
CFRP_DENSITY = 1550               # kg/m³, carbon fiber composite density
AIRFOIL_THICKNESS_RATIO = 0.14    # t/c, typical for HALE airfoils (14%)
STRUCTURAL_LOAD_FACTOR = 1.2      # design gust load factor (stratospheric HALE)
SKIN_AREAL_DENSITY = 0.3          # kg/m², wing covering (film + ribs, not solid CFRP)

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

# ── Night descent ─────────────────────────────────────────────────────────
NIGHT_DESCENT_M = 0.0             # altitude traded during night (m), 0 = level flight
CLIMB_POWER_FRACTION = 0.80       # fraction of daytime excess power used for climbing
#   Remaining 20% goes to battery charging

# ── Mission ───────────────────────────────────────────────────────────────
DEFAULT_LATITUDE = 30.0           # degrees N
DEFAULT_DAY_OF_YEAR = 172         # ~summer solstice
MIN_ENDURANCE_DAYS = 30           # mission duration target

# ── Cost ──────────────────────────────────────────────────────────────────
DEFAULT_PRODUCTION_RUN = 10       # fleets built (for capital amortization)
