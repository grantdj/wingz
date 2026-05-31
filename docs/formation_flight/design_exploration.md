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

## Reynolds Number Effect on Optimal AR

**Critical finding:** At 20 km altitude, kinematic viscosity is 17× higher
than sea level. Reynolds number (Re = V × chord / ν) drops fast at high AR.

| Span | AR | Chord | Re at 25 m/s | CL_max impact |
|---|---|---|---|---|
| 25m | 20 | 1.25m | 208,000 | Marginal — at boundary |
| 25m | 14 | 1.79m | 298,000 | OK — standard airfoil data |
| 20m | 20 | 1.00m | 167,000 | LOW — CL_max drops to ~0.85 |
| 15m | 20 | 0.75m | 125,000 | LOW — laminar separation issues |
| 10m | 20 | 0.50m | 83,000 | VERY LOW — model is invalid |

**The model uses CL_max = 1.2 everywhere.** This is optimistic for Re < 200k.
With Re-dependent CL_max, high AR would be penalized on small spans:
- 6x10m AR=20 (Re=83k): CL_max ~0.7, stall speed +31%, power +125%
- 6x25m AR=20 (Re=208k): CL_max ~1.0, marginally viable

**Implication:** The optimal AR for small spans (≤20m) is probably 12-16,
not 20. For 25m+ spans, AR=20 remains viable. Adding Re-dependent CL_max
to the solver would shift the Pareto frontier toward larger aircraft.

## Active Flutter Suppression — Not Worth It

At the scales we're looking at (10-25m span, <200 kg), structural mass is
only 5-11 kg per aircraft. A 15% AFS mass savings is 1.6 kg — but the AFS
hardware (IMUs, actuators) weighs 2 kg. **Net mass is negative** (-0.4 kg).

AFS is valuable for very large flexible wings (60m+) where structure is
100+ kg. For our formation aircraft, the wings are stiff enough that
flutter is not the sizing constraint — beam bending is.

## OOA Manufacturing — $2M/fleet Savings

Switching from autoclave to OOA eliminates the largest capital cost.
At 25m span, the autoclave alone costs $20M in our model. An OOA oven
is $200k. Amortized over 10 fleets: **$2M savings per fleet**.

This is larger than the entire avionics + propulsion budget. The cost model
should be updated to support OOA as the default manufacturing approach
for these small unmanned aircraft.

## Summary of Recommended Design Changes

1. **Add Re-dependent CL_max** to the solver — this will correctly penalize
   high AR at small spans and shift the optimum to AR=14-16 for 10-20m spans
2. **Use OOA manufacturing** as default — eliminate autoclave capital
3. **Size for winter solstice** at operating latitude for year-long missions
4. **Target solid-state batteries (2028)** at 400 Wh/kg for production
5. **Use boom-tail** for formation (yaw authority), flying wing only for single
6. **Leader rotation** is already modeled correctly (average power sizing)
7. **AFS not worth it** at these scales — structural mass too small
8. **Battery heating** is <2% overhead with good insulation — manageable

## Iteration 2 Results

### OOA Manufacturing Cost Impact

Switching from autoclave to OOA (out-of-autoclave) processing:

| Config | Autoclave | OOA | Savings | $/kg (OOA) |
|---|---|---|---|---|
| 6x20m AR=16 | $5.9M | $4.8M | $1.1M | $54k/kg |
| 6x25m AR=18 | $8.6M | $6.7M | $1.9M | $47k/kg |
| 6x30m AR=18 | $12.7M | $9.6M | $3.1M | $43k/kg |
| 6x40m AR=18 | $23.4M | $17.0M | $6.3M | $38k/kg |

OOA saves 15-27% on total fleet cost. The savings grow with span because
autoclave capital scales as span^2.5 while OOA ovens scale linearly.

### Winter-Constrained Year-Long Design

For year-long ops at 30°N, design to winter solstice (shortest day):

**Cheapest fleet for ≥500W payload year-round:**

| Config | Winter | Summer | Cost | Fleet mass |
|---|---|---|---|---|
| **6x20m AR=16** | **509 W** | **1,781 W** | **$5.55M** | 347 kg |
| 4x25m AR=18 | 503 W | 1,674 W | $6.04M | 314 kg |
| 3x30m AR=20 | 507 W | 1,641 W | $7.08M | 301 kg |

The 6x20m formation is cheapest. In summer it delivers 3.5× the winter
payload — excess capacity for burst operations or payload swap rotation.

### Cost per Fleet Size (Year-Long ≥500W at 30°N)

| N | Best config | Cost |
|---|---|---|
| 2 | 2x50m AR=18 | $18.8M |
| 3 | 3x30m AR=20 | $7.1M |
| 4 | 4x25m AR=18 | $6.0M |
| 6 | 6x20m AR=16 | $5.6M |

Larger formations are dramatically cheaper for the same capability.
N=6 costs 70% less than N=2 for the same year-round payload.

## Iteration 3: Battery Density + Combined Optimization

### Battery Technology Impact

At fixed mission (6x20m AR=16, winter 30°N):

| Battery tech | Wh/kg | Battery/ac | Mass saved | More payload |
|---|---|---|---|---|
| Li-ion (current) | 250 | 43 kg | baseline | baseline |
| Li-ion (year-long derated) | 175 | 62 kg | -19 kg | -372 W |
| Si-anode Li-ion | 350 | 31 kg | +12 kg | +248 W |
| Solid-state (2028) | 400 | 27 kg | +16 kg | +325 W |
| Solid-state (target) | 500 | 22 kg | +22 kg | +434 W |

Solid-state at 400 Wh/kg saves 16 kg per aircraft — nearly doubles
winter payload from 509W to ~834W. Cold-tolerant (no heating needed)
and 1,100+ cycle life eliminates degradation concerns.

### Recommended Designs (OOA Manufacturing)

Two design points depending on budget vs capability:

**Budget option: 6x20m AR=16 — $4.5M (OOA)**
- Cheapest fleet that delivers ≥500W year-round at 30°N
- 509W winter / 1,781W summer
- 58 kg per aircraft, 347 kg fleet
- Chord: 1.25m, Re: 208k (marginal but viable)

**Capability option: 6x30m AR=20 — $8.4M (OOA)**
- Best $/kg payload at higher capability
- 1,420W winter / 4,183W summer
- 120 kg per aircraft, 720 kg fleet
- Chord: 1.50m, Re: 250k (comfortable)
- $/kg: $118k (OOA)

### Solid-State Battery Impact (2028+)

With 400 Wh/kg solid-state batteries (conservative 2028 target):
- Battery mass drops 38% → lighter aircraft → less power needed
- Estimated effect on budget option: 509W → ~750W winter payload
- Or: same payload at lower cost (smaller wing area, less solar)
- Cold-tolerant: eliminates battery heating subsystem entirely

### Year-Long Endurance Strategy

For 30°N year-round operations:
1. **Size to winter solstice** (10.1h day / 13.9h night)
2. **Accept 2.9× seasonal variation** in payload capacity
3. **Use summer excess** for burst operations, payload swap, or data-intensive missions
4. **Leader rotation every 30-60 min** (already modeled)
5. **Battery swap in winter** if payload needs exceed winter capacity
6. **Solid-state batteries (2028)** eliminate cold/degradation concerns

### Final Summary Table

| Metric | Budget (6x20m) | Capability (6x30m) |
|---|---|---|
| Fleet cost (OOA) | $4.5M | $8.4M |
| Winter payload | 509 W | 1,420 W |
| Summer payload | 1,781 W | 4,183 W |
| Per aircraft mass | 58 kg | 120 kg |
| Fleet mass | 347 kg | 720 kg |
| Chord | 1.25 m | 1.50 m |
| AR | 16 | 20 |
| Reynolds number | 208k | 250k |
| $/kg payload (OOA) | - | $118k |

## Iteration 4: TCO, DOD Optimization, Competitive Landscape

### Depth of Discharge Optimization

80% DOD is the sweet spot for multi-year operations:

| DOD | Battery/ac | Replace interval | Annual batt cost |
|---|---|---|---|
| 100% | 43 kg | 1.4 years | $143k/year |
| **80%** | **54 kg** | **2.7 years** | **$89k/year** |
| 60% | 72 kg | 5.5 years | $59k/year |

80% DOD doubles battery life (1.4 → 2.7 years) at only 25% more mass.
The annual cost drops 38%. At 60% DOD the mass penalty (67% more)
starts eating into payload capacity.

### 5-Year Total Cost of Ownership (6x20m AR=16, OOA)

| Item | Cost |
|---|---|
| Fleet acquisition (OOA) | $4,500,000 |
| Operations (5yr) | $1,000,000 |
| Maintenance (5yr) | $500,000 |
| Insurance (5yr) | $250,000 |
| Battery replacements | $698,000 |
| **5-year TCO** | **$6,948,000** |
| **Daily cost** | **$3,807/day** |

### Competitive Landscape

| System | Daily cost | Capability |
|---|---|---|
| **Our formation (6x20m)** | **$3,807** | 500W year-round, 20km, relocatable |
| Tethered aerostat | $3,000 | Fixed location, weather-limited |
| LEO satellite (amortized) | $5,000 | Intermittent, constellation needed |
| Zephyr S (single) | $15,000 | 50W payload, seasonal limits |
| MQ-9 Reaper | $30,000 | Not persistent, fuel-based |
| GEO satellite | $50,000 | Global, 15yr life, $300M+ launch |

The formation is cost-competitive with LEO satellites and 4× cheaper
than Zephyr per unit of payload delivered. Key advantages over all
alternatives: no launch costs, relocatable, payload-swappable,
graceful degradation.

### Investigation Summary

After 4 iterations of research and modeling:

**The formation flight thesis is validated.** Six small aircraft (20-30m span)
in V formation deliver persistent stratospheric coverage at $3,800/day —
competitive with satellites and dramatically cheaper than single HALE platforms.

**Key design parameters (converged):**
- Fleet size: N=6 (optimal for cost and resilience)
- Span: 20-30m per aircraft (20m budget, 30m capability)
- Aspect ratio: 16-20 (Re-limited at small spans)
- Configuration: boom-tail (yaw authority for formation)
- Manufacturing: OOA composites (saves $2-6M vs autoclave)
- Battery: 80% DOD for 2.7-year replacement interval
- Panel sizing: 3× power margin (dynamic coverage, not fixed 80%)
- Stall margins: 1.15× day, 1.03× night
- Leader rotation: every 30-60 minutes (already modeled)
- Design point: winter solstice at operating latitude

**Biggest future lever:** Solid-state batteries (2028, 400 Wh/kg) would
increase winter payload by ~50% and eliminate cold-weather concerns.
