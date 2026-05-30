# Equation References

Every equation in the wingz package traced to its source.

## Aerodynamics

### Induced Drag

`D_i = W² / (q π e b²)`

Used in: `wingz/aerodynamics/drag.py`

Derived from the lift coefficient definition and induced drag coefficient for
an elliptically loaded wing. Combines `C_Di = C_L² / (π e AR)` with
`D_i = q S C_Di` and `AR = b²/S` to eliminate area.

- Anderson, J.D., *Fundamentals of Aerodynamics*, 6th ed., McGraw-Hill, 2017. Chapter 5, Section 5.3.3 — "Induced Drag" (Eq. 5.63, 5.66)
- Prandtl, L., "Tragflügeltheorie," *Nachrichten von der Gesellschaft der Wissenschaften zu Göttingen*, 1918. (Lifting-line theory origin)

### Parasite Drag

`D_p = q S C_D0`

Used in: `wingz/aerodynamics/drag.py`

Standard form drag. C_D0 is the zero-lift drag coefficient encompassing
skin friction and form drag.

- Anderson, J.D., *Fundamentals of Aerodynamics*, 6th ed., Chapter 5, Section 5.2

### Dynamic Pressure

`q = ½ ρ V²`

Used in: `wingz/mission/profiles.py`

- Any introductory aerodynamics text. Anderson Ch. 3.

## Formation Aerodynamics

### Wake Drag Reduction Factor

`factor = 1.0 - 0.35 · exp(-(r - 0.1)² / (2 · 0.15²))`

Used in: `wingz/aerodynamics/formation_aero.py`

Parameterized Gaussian model capturing the key result from classical formation
flight theory: a trailing aircraft in the upwash of a leader's wingtip vortex
sees reduced induced drag, with optimal benefit at ~10% lateral overlap.

The 35% maximum reduction and Gaussian shape are simplified fits to:

- Lissaman, P.B.S. and Shollenberger, C.A., "Formation Flight of Birds," *Science*, Vol. 168, No. 3934, 1970, pp. 1003–1005. doi:10.1126/science.168.3934.1003
- Hummel, D., "Aerodynamic Aspects of Formation Flight in Birds," *Journal of Theoretical Biology*, Vol. 104, No. 3, 1983, pp. 321–347. doi:10.1016/0022-5193(83)90110-8
- Hummel, D., "Formation Flight as an Energy-Saving Mechanism," *Israel Journal of Zoology*, Vol. 41, 1995. Also available as ADA256861.

NASA experimental validation:

- Vachon, M.J. et al., "F/A-18 Performance Benefits Measured During the Autonomous Formation Flight Project," AIAA 2003-6479, 2003.
- Ray, R.J. et al., "Flight Test Techniques Used to Evaluate Performance Benefits During Formation Flight," AIAA 2002-4492, 2002.

### Effective Span

`b_eff = N · b / √(Σ factor_i)`

Used in: `wingz/aerodynamics/formation_aero.py`

Derived by setting the formation's total induced drag equal to what a single
aircraft with span b_eff would produce carrying the same total weight:

For N identical aircraft each carrying W/N at span b:

    D_i_formation = Σ (factor_i · (W/N)² / (q π e b²))
                  = W² / (q π e) · Σ(factor_i) / (N² b²)

Setting equal to D_i_equiv = W² / (q π e b_eff²):

    b_eff² = N² b² / Σ(factor_i)
    b_eff  = N b / √(Σ factor_i)

This is an original derivation for this project, combining standard induced drag
theory with per-slot formation factors.

### V-Formation Slot Factors

Used in: `wingz/aerodynamics/formation_aero.py`

The diminishing-returns model for deeper V positions and the dual-wake benefit
for interior aircraft are informed by:

- Bangash, Z.A. et al., "Aerodynamics of Formation Flight," *Journal of Aircraft*, Vol. 43, No. 4, 2006, pp. 907–912.
- Ning, S.A., Flanzer, T.C., and Kroo, I.M., "Aerodynamic Performance of Extended Formation Flight," *Journal of Aircraft*, Vol. 48, No. 3, 2011, pp. 855–865.

Symmetry between left/right slots in zero crosswind follows from the mirror
symmetry of the trailing vortex system. Crosswind, asymmetric loading, or
heterogeneous aircraft break this symmetry.

## Structural Scaling

### Empirical Wing Mass

`m_wing = a · b^n`

Used in: `wingz/structures/empirical.py`

Power-law fit to real solar/HALE aircraft data using scipy curve_fit.
The fitted exponent (~2.4) is consistent with structural scaling analysis:

- Raymer, D.P., *Aircraft Design: A Conceptual Approach*, 6th ed., AIAA, 2018. Chapter 15 — "Weights" (wing weight estimation methods, Eq. 15.1–15.5)
- Torenbeek, E., *Synthesis of Subsonic Airplane Design*, Springer, 1982. Chapter 8 — "Weight estimation" (cantilever wing scaling)
- Roskam, J., *Airplane Design*, Part V: "Component Weight Estimation," DAR Corporation, 1999.

For context on why the exponent exceeds 2.0 (cube-law deflection driving
stiffness requirements):

- Euler-Bernoulli beam theory: δ = FL³ / (3EI) — deflection grows with span³
- MIT OCW 2.080J, *Structural Mechanics*, Fall 2013 — beam bending fundamentals

### Data Sources

The calibration data (Zephyr S, PHASA-35, Pathfinder Plus, Odysseus, Helios,
HAPSMobile Sunglider, Solar Impulse 2) wing masses are estimates derived from
published MTOW and typical structural fractions for solar/HALE platforms.

Published specifications:
- Zephyr: Airbus Defence and Space product data sheets
- PHASA-35: BAE Systems press releases (2019–2020)
- Pathfinder Plus: NASA/TM-2001-210222
- Helios: NASA/TM-2004-212854
- HAPSMobile Sunglider: SoftBank/HAPSMobile press releases
- Solar Impulse 2: Solar Impulse Foundation technical documentation
- Odysseus: Boeing Aurora Flight Sciences press releases (2019)

## Solar Power

### Solar Irradiance at Altitude

`I = I₀ · exp(-τ · AM)`

where:
- `τ = τ₀ · exp(-h / H)` — optical depth at altitude h
- `AM = 1 / sin(α)` — airmass at solar elevation α
- `sin(α) = sin(φ) sin(δ) + cos(φ) cos(δ)` — peak solar elevation

Used in: `wingz/solar/power.py`

Constants: I₀ = 1361 W/m² (solar constant), H = 8500 m (scale height),
τ₀ = 0.3 (sea-level clear-sky optical depth).

- Iqbal, M., *An Introduction to Solar Energy*, Academic Press, 1983. Chapter 6 — atmospheric transmission
- Kasten, F. and Young, A.T., "Revised Optical Air Mass Tables and Approximation Formula," *Applied Optics*, Vol. 28, No. 22, 1989.
- ASTM E490 — Standard Solar Constant and Zero Air Mass Solar Spectral Irradiance Tables

### Solar Declination

`δ = 23.45° · sin(360°/365 · (DOY - 81))`

Used in: `wingz/solar/power.py`

Standard approximate formula for seasonal variation of the sun's declination.

- Spencer, J.W., "Fourier Series Representation of the Position of the Sun," *Search*, Vol. 2, No. 5, 1971.
- Duffie, J.A. and Beckman, W.A., *Solar Engineering of Thermal Processes*, 4th ed., Wiley, 2013. Chapter 1.

### Day Length

`cos(ω_s) = -tan(φ) · tan(δ)`

`day_hours = 2ω_s · 12/π`

Used in: `wingz/solar/power.py`

CBM (Brock) model for sunrise/sunset hour angle.

- Brock, T.D., "Calculating Solar Radiation for Ecological Studies," *Ecological Modelling*, Vol. 14, 1981, pp. 1–19.
- Duffie and Beckman, Chapter 1.

### Daily Energy (Sinusoidal Averaging)

`E = P_avg · day_hours`

`P_avg = (2/π) · P_peak`

Used in: `wingz/solar/power.py`

The 2/π factor comes from the average value of sin(x) over [0, π],
approximating the sinusoidal variation of solar elevation through the day.

- Standard integral: (1/π) ∫₀^π sin(x)dx = 2/π

### Energy Balance

`surplus = E_available - P_required · 24`

Used in: `wingz/solar/energy_balance.py`

For perpetual flight (30+ days), the aircraft must close the energy balance
every 24-hour cycle. This is the fundamental feasibility constraint for
solar HALE platforms.

- Noth, A., "Design of Solar Powered Airplanes for Continuous Flight," PhD Thesis, ETH Zurich, 2008. (Definitive treatment of solar aircraft energy balance)
- Leutenegger, S. et al., "Solar Airplane Conceptual Design and Performance Estimation," *Journal of Intelligent & Robotic Systems*, Vol. 61, 2011.

### Battery Mass

`m_battery = P · t_night / ε`

Used in: `wingz/solar/energy_balance.py`

Default ε = 250 Wh/kg (current Li-ion). Near-term Li-S: ~400 Wh/kg.

- Noth (2008), Chapter 3 — battery sizing for solar aircraft

## Station Keeping

### Station-Keeping Power

`P_sk = k · T_eff · (1/d) · b^1.5`

where T_eff = turbulence_intensity × wake_factor

Used in: `wingz/control/station_keeping.py`

Empirical model. The span^1.5 exponent reflects that correction forces scale
with wing loading (area × dynamic pressure) and the moment arm of control
surfaces. The inverse tolerance reflects increased control effort for tighter
formation spacing.

- Pahle, J. et al., "An Initial Flight Investigation of Formation Flight for Drag Reduction on the C-17 Aircraft," AIAA 2012-4802, 2012. (Measured station-keeping workload)
- Hanson, C.E. et al., "The DARPA/NASA Automated Airborne Refueling Demonstration," AIAA 2006-6610, 2006. (Precision relative navigation requirements)

The k=50 constant and specific scaling are calibrated for order-of-magnitude
reasonableness, not validated against flight data. This model should be
replaced with higher-fidelity estimates as the project matures.

## Cost Models

### Mass Proxy

`cost = (w_s · m_struct + w_c · m_ctrl) · N^α`

Used in: `wingz/cost/mass_proxy.py`

Default: w_s=1.0, w_c=2.0 (control hardware is more expensive per kg), α=1.2.
No published source — this is a project-specific proxy to avoid fabricating
dollar values when per-unit cost data for solar HALE platforms is unavailable.

### Bottom-Up Materials

`cost = C_cf·m + C_solar·A + C_avionics·m_ctrl + C_bat·E + C_asm·m`

Used in: `wingz/cost/materials.py`

Component pricing based on market surveys:
- Carbon fiber composite: ~$120/kg — aerospace supply chain pricing
- Flexible solar cells: ~$800/m² — Alta Devices / SunPower thin-film pricing
- Avionics: ~$5000/kg — tactical UAV component costs (GPS, IMU, comms)
- Li-ion batteries: ~$300/kWh — 2024 cell-level pricing
- Assembly: ~$200/kg structure — rough aerospace labor estimate

These are order-of-magnitude estimates. The materials cost model is a
research area that will evolve as better data becomes available.

## Atmosphere Model

### International Standard Atmosphere

Used in: `wingz/mission/atmosphere.py`

T = T₀ - L·h (troposphere, 0-11km)
T = T_tropopause (lower stratosphere, 11-20km)
P = P₀ · (T/T₀)^(g/(L·R)) (troposphere)
P = P_trop · exp(-g·(h-h_trop)/(R·T_trop)) (stratosphere)
ρ = P/(R·T) (ideal gas)

References:
    ICAO Standard Atmosphere, ICAO Doc 7488/3, 1993.
    US Standard Atmosphere, 1976 (NASA-TM-X-74335).

## Thrust Power

`P_thrust = D · V`

Used in: `wingz/evaluation/sweep.py`

- Anderson, *Fundamentals of Aerodynamics*, Chapter 5 (power required for level flight)
