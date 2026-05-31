# Design Exploration — Deep Dive

*2026-05-31. Synthesis of research + model sweeps across AR, cost, batteries,
flying wings, leader rotation, seasonal ops, and year-long endurance.*

## AR = 20 Investigation

The design search found AR=20 optimal at every fleet size. Investigation:

**Manufacturing reality:** Higher AR is NOT more expensive for unmanned
composite aircraft. The cost driver is **span** (tooling length, autoclave
length, handling), not chord. A 1.25m chord wing at 25m span is
manufacturing-friendly — well above the practical minimum (~0.25m).

- OOA (out-of-autoclave) processing eliminates the autoclave entirely
  with <5% structural penalty. Zephyr uses OOA.
- Pultruded spar caps get CHEAPER at high AR (constant cross-section,
  marginal cost near zero). ORNL data: 39% cheaper than infused.
- AFP (automated fiber placement) favors long uniform structures.

**Conclusion:** The cost model's span-dependent pricing (not AR-dependent)
is correct. AR=20 with 1.25m chord is buildable and cheap. The model
is not overfitting — AR genuinely doesn't penalize manufacturing for
unmanned OOA composites.

**Panel coverage explains the cost:** At AR=20, wing area is small (31 m²/ac
for 25m span). Panel coverage at max payload hits 90% (ceiling). At lower AR,
the wing is bigger (78 m² at AR=8) and coverage is 90% — meaning 70% more
solar panel area for roughly the same payload. Solar cells at $100/W dominate
cost, so less wing area = less cost.

## Battery Technology for Year-Long Missions

### Temperature at Altitude

At 20 km, ambient temperature is -55°C. Li-ion batteries need heating:

| Insulation | Heating power/ac | Fleet overhead |
|---|---|---|
| Aerogel (excellent) | 18 W | 0.5% of night power |
| Foam (good) | 35 W | 0.9% |
| Basic | 70 W | 1.8% |

Battery heating is a small overhead (< 2%) with decent insulation.

### Cycle Degradation

365 cycles at 100% DOD → ~80-85% SOH (15-20% capacity loss).
Effective Wh/kg for year-long: 250 × 0.82 × 0.85 = **175 Wh/kg** (Li-ion).
This would increase battery mass by 43%.

### Battery Technology Options

| Technology | Wh/kg | Cycle life | Cold tolerance | Year-long viable? |
|---|---|---|---|---|
| Li-ion (NMC) | 250 (175 eff) | 500 @ 100% DOD | Needs heating | Yes, with derating |
| Li-S (Sion/Zephyr) | 400-450 | 50-200 | Good at cold | No — dies in 3 months |
| Solid-state (2028) | 400 | 1,100+ | -30 to +80°C | **Ideal** — cold-tolerant, high cycle |
| Si-anode Li-ion | 320-480 | 300-1000 | Similar to NMC | Marginal at high DOD |

**Recommendation:** Design for 250 Wh/kg now (conservative), target solid-state
at 400 Wh/kg for 2028+ production. Solid-state is the game-changer: cold-tolerant,
high cycle life, 60% more energy density.

## Flying Wing Configuration

### Control Authority

Flying wings use split drag rudders or differential thrust for yaw. Yaw authority
is 30-50% of a conventional rudder — marginal for tight formation keeping.
For formation flight, this means:

- Station-keeping tolerance may need to relax (3-4m instead of 2m)
- Differential thrust (two motors) provides better yaw response
- No published examples of flying wing UAVs in close formation exist

### Helios Crash Lesson

Helios (flying wing, 75m span) crashed when turbulence caused excessive dihedral
deflection → undamped pitch divergence → structural failure. Root cause:
no active pitch damping and insufficient analysis of dihedral-coupled instability.

**Implication:** Flying wing formations need active stability augmentation.
The 10-20m span aircraft in our study are much stiffer than Helios (75m) —
flutter/stability risk is lower, but still needs active control.

### Active Flutter Suppression

- Can raise flutter speed by ~37% (ML controller, Journal of Sound & Vibration 2022)
- Enables 10-20% structural mass reduction by relaxing stiffness constraints
- Hardware: a few kg of IMUs/actuators + 50-100W — small overhead
- TRL 4-5 for HALE applications. Not flight-proven for mass savings yet.

### Flying Wing Cd0 Advantage

- 15-25% lower Cd0 vs boom-tail (no boom/tail wetted area)
- BUT: reflexed airfoil reduces CL_max by 15-25% and L/D by 5-10%
- Net effect: lower drag at cost of higher wing loading / stall speed

## Leader Rotation

Our model already assumes leader rotation implicitly — battery is sized to
fleet-average power, not worst-case leader power.

**Rotation mechanics:**
- Swap takes 1-3 minutes (Airbus fello'fly data)
- Energy cost: 0.5-1.5% of saved fuel during formation segment
- Optimal frequency: every 30-60 minutes for identical aircraft
- With N=6: each aircraft leads 10 min/hour, follows 50 min/hour

**Impact on design:** Leader rotation means all aircraft are identical
(same battery, same structure). This is already our assumption.
No model change needed — we're already modeling the rotated case.

## Seasonal Operations for Year-Long Endurance

### Payload Capacity by Season (6x25m AR=20, 30°N)

| Season | Day hours | Payload power |
|---|---|---|
| Summer | 13.9h | 3,940 W |
| Equinox | 12.0h | 2,321 W |
| Winter | 10.1h | 1,423 W |

Winter payload is 64% less than summer. Options:

1. **Seasonal payload adaptation** — run lighter payloads in winter
2. **Latitude migration** — fly south in winter (+20% payload at 20°N)
3. **Battery swap rotation** — land aircraft for battery swap before dawn
4. **Accept reduced capability** — design to winter minimum (1,423 W)

### Year-Long Design Point

If the system must maintain minimum payload year-round, design to the
**winter solstice at operating latitude**. At 30°N, that's 1,423 W.
The same fleet produces 3,940 W in summer — 2.8× seasonal variation.

## Alternative ConOps

### Altitude Migration
Fly lower in winter (15-18 km) where air is denser:
- Lower cruise speed needed for same wing loading
- Less power required for level flight
- Closer to weather — more turbulence risk

### Latitude Migration
Move equatorward in winter:
- 20°N in Dec: 10.8h day vs 10.1h at 30°N
- Modest improvement (+20% payload power)
- Operational complexity of repositioning

### Relay Operations
Station two formations at different latitudes:
- Northern formation: summer operations
- Southern formation: winter operations
- Hand off coverage as seasons change
- Doubles fleet cost but maintains year-round capability

### Hybrid with Ground Backup
Use formations for good-weather months (March-September at 30°N),
supplement with ground-based assets or LEO satellites in winter.
Reduces the year-round endurance requirement.
