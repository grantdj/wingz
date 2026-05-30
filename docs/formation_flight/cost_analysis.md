# Cost Analysis — Formation vs Single Aircraft

*Updated 2026-05-30 with realistic aerospace pricing.*

## Cost Model

The previous cost model used consumer/commodity pricing ($800/m² solar, $300/kWh
battery). The updated model uses aerospace-grade pricing based on 2024-2026
market data:

| Component | Price | Source |
|---|---|---|
| III-V solar cells | $100/W ($30,000/m²) | MicroLink ELO, mid-volume |
| Aerospace Li-ion pack | $3,000/kWh | Qualified pack with BMS |
| CFRP finished structure | $350/kg | Prepreg + autoclave + labor |
| Full nav suite | $25,000 per unit | Redundant IMU, dual RTK, SATCOM |
| Basic autopilot | $1,500 per unit | Flight computer + GPS |
| Relative nav sensor | $500 per unit | UWB/visual for followers |
| Propulsion combo | $900 per unit | Motor + ESC + propeller |
| Assembly labor | $300/kg structure | Integration & test |
| GCS (portable tactical) | $30,000 per fleet | Shared across formation |
| Launch/recovery equipment | $100,000 per fleet | HALE ground equipment |
| Wing mold tooling | $100,000 amortized | Per unique span, over production run |

### What changed

**Solar cells went from $800/m² to $30,000/m².** This is the dominant cost
change. III-V multi-junction cells at $100/W and ~300 W/m² at altitude cost
roughly $30,000 per square meter — 37x our previous estimate. Solar cells
now represent 75-93% of total system cost.

**Batteries went from $300/kWh to $3,000/kWh.** Aerospace qualification
(custom BMS, vibration testing, altitude cycling) adds ~10x over cell-level
pricing.

**Structure is now $350/kg** (finished parts, up from $120/kg raw material +
$200/kg assembly = $320/kg, roughly similar).

### What's still missing

- Development/NRE ($50M-200M for a new HALE platform — amortized over fleet)
- Certification costs
- Annual operations (crew, maintenance, spares)
- Insurance
- Payload equipment cost (sensors, comms — mission-dependent)

## Results: Fixed Payload Missions

All comparisons at AR=25, 38% MicroLink III-V panels, 30°N summer, 20km altitude.
Production run of 10 fleets for tooling amortization.

### Surveillance Mission (200W / 20kg payload)

| Config | Total Cost | $/W payload | Solar cost | Solar % of total |
|---|---|---|---|---|
| 1x60m | $4,642,927 | $23,215 | $4,320,000 | 93% |
| 2x30m | $2,419,650 | $12,098 | $2,160,000 | 89% |
| 4x15m | $1,310,435 | $6,552 | $1,080,000 | 82% |
| 6x10m | $943,782 | $4,719 | $720,000 | 76% |

### Multi-Sensor Mission (1kW / 100kg payload)

| Config | Total Cost | $/W payload | Solar cost | Solar % of total |
|---|---|---|---|---|
| 1x60m | $4,667,086 | $4,667 | $4,320,000 | 93% |
| 2x30m | $2,443,809 | $2,444 | $2,160,000 | 88% |
| 4x15m | $1,334,594 | $1,335 | $1,080,000 | 81% |
| 6x10m | $967,941 | $968 | $720,000 | 74% |

### Key Finding

**Solar cell cost dominates everything.** At $100/W, the III-V cells on
a single 60m aircraft cost $4.3M. The formation's smaller wing area directly
translates to lower cost: 4x15m saves $3.2M on solar cells alone.

The cost advantage of formation flight is driven almost entirely by
**using less wing area** — which means less solar panel area, which means
fewer extremely expensive III-V cells.

## The 2x30m Sweet Spot

The 2x30m configuration deserves special attention:

- **Simplest formation** — one leader, one follower
- **Lowest control complexity** — only one pair to coordinate
- **Half the solar cost** of single 60m ($2.16M vs $4.32M)
- **50-55% the total cost** across all payload missions
- **Enough energy capacity** for substantial payloads (400%+ at 200W)
- **Graceful degradation** — lose the follower, the leader can still fly solo

At every mission payload level, the 2x30m costs roughly half what the 1x60m
costs, with a much simpler control problem than 4+ aircraft formations.

## Heterogeneous Payload Distribution

In a formation, payload doesn't need to be split evenly. Each aircraft can
carry different equipment optimized for its role:

### 2x30m: Where to put a 1kW/100kg payload?

| Strategy | Leader mass | Nav mass | Total drag | Total power |
|---|---|---|---|---|
| A: All on navigator (wake) | 21.2 kg | 123.3 kg | 36.8 N | 937 W |
| B: Split evenly | 71.2 kg | 73.3 kg | 34.2 N | 873 W |
| C: All on leader (front) | 121.2 kg | 23.3 kg | 43.6 N | 1107 W |

**Splitting evenly wins on drag** — concentrating mass creates a W² penalty
in induced drag that outweighs the 35% wake benefit. Putting all payload on
the leader (front, no wake help) is worst.

The optimal strategy depends on the mission:
- For **minimum drag**: split evenly
- For **sensor pointing**: concentrate on navigator (stable wake position)
- For **resilience**: distribute different capabilities across aircraft

### 4x15m: Specialized Roles

| Aircraft | Position | Payload | Power | Mass |
|---|---|---|---|---|
| Leader | Front (clean air) | None — just flies | 0 W | 0 kg |
| Navigator | 1st wake slot | Formation control + comms relay | 50 W | 5 kg |
| Sensor | 2nd wake (left) | EO/IR surveillance camera | 200 W | 20 kg |
| Relay | 2nd wake (right) | High-bandwidth datalink | 500 W | 30 kg |
| **Total** | | **Distributed ISR platform** | **750 W** | **55 kg** |

This is a distributed ISR (intelligence, surveillance, reconnaissance) platform
where each aircraft specializes in one function. Lose one follower, you lose
one capability — not the entire mission. The navigator can reassign roles or
the formation degrades gracefully.

A single aircraft carrying all this on one airframe needs all the redundancy
built in to avoid total loss. The formation gets resilience for free through
distribution.

## Cost per Payload Watt — The Bottom Line

| Payload | 1x60m $/W | 2x30m $/W | 4x15m $/W | 6x10m $/W |
|---|---|---|---|---|
| 200 W | $23,215 | $12,098 | $6,552 | $4,719 |
| 500 W | $9,286 | $4,839 | $2,621 | $1,888 |
| 1,000 W | $4,667 | $2,444 | $1,335 | $968 |
| 2,000 W | $2,358 | $1,246 | $692 | $509 |

**Formation is 3-5x cheaper per watt of payload** across all mission sizes,
driven primarily by solar cell cost reduction from smaller total wing area.

The cost advantage is strongest for small payloads (5x at 200W) because the
single aircraft's excess wing area is pure overhead. It narrows for larger
payloads (3x at 2kW) as batteries become a larger cost fraction.
