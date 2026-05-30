# Payload Swap and Mission Rotation

## Concept

Every aircraft in the formation is an identical airframe with a standardized
payload bay. The formation maintains continuous on-station presence while
individual aircraft rotate to the ground for payload swaps, battery swaps,
or maintenance. This is a capability unique to formations — a single aircraft
must land to change its mission, terminating coverage entirely.

## How It Works

1. One aircraft descends from the formation
2. On the ground: payload module is swapped (sensors, comms, batteries)
3. Aircraft relaunches and climbs back to formation altitude (~2 hours)
4. Rejoins formation, another aircraft rotates down

The formation flies with N-1 aircraft during the swap window. The remaining
aircraft reform into a smaller V and continue the mission at reduced capacity.

## Formation Degradation During Rotation

| Formation | N-1 flying | Drag penalty | Effective span loss | Solar loss |
|---|---|---|---|---|
| 2 → 1 | 50% fleet | +21% avg drag | 36% span loss | 50% |
| 4 → 3 | 75% fleet | +14% avg drag | 19% span loss | 25% |
| 6 → 5 | 83% fleet | +8% avg drag | 12% span loss | 17% |

The 2-aircraft formation is fragile — losing one aircraft to rotation
eliminates all payload capacity (the leader carries no payload). The
4-aircraft and 6-aircraft formations degrade gracefully, maintaining
useful capability throughout the swap window.

## Rotation Schedule

A 4-aircraft formation with 6-hour rotation cycles:

- Each aircraft: 18h on-station, 6h on-ground per day
- 3 aircraft always flying (75% availability)
- 4 payload swaps per day across the fleet

### Example: Multi-Mission 24h Rotation

| Window | On-Station | On-Ground | Payload Config |
|---|---|---|---|
| 00:00–06:00 | AC1, AC2, AC3 | AC4 (swap) | Night ISR: SAR radar on AC3 |
| 06:00–12:00 | AC1, AC2, AC4 | AC3 (swap) | Morning surveillance: EO/IR on AC4 |
| 12:00–18:00 | AC1, AC3, AC4 | AC2 (swap) | Afternoon comms: relay on AC3 |
| 18:00–24:00 | AC2, AC3, AC4 | AC1 (swap) | Evening survey: LIDAR on AC2 |

Each 6-hour window delivers a different mission type. Over 24 hours, the
single fleet has provided ISR, surveillance, communications relay, and
wide-area survey — from four identical airframes with swappable payload
modules.

## Battery Swap

Battery swap is a special case of payload rotation that extends the formation's
operational envelope:

- **Winter operations**: Short days may not provide enough solar to close the
  24h energy cycle. Rotate aircraft down for battery swap before dawn.
- **High-latitude missions**: Same concept, compensating for reduced solar.
- **Extended burst payload**: Run high-power payloads that drain the battery
  faster than solar can replenish, then swap to a fresh battery.
- **Battery health**: Swap degraded packs without retiring the airframe.

A ground crew with charged battery packs turns the formation into a
relay system where energy is delivered from the ground via battery swap
rather than collected entirely from solar.

## Maintenance Rotation

Continuous maintenance without mission interruption:

- Inspect one aircraft at a time on the ground while N-1 continue flying
- Replace worn components (propellers, control surfaces) without grounding fleet
- Software updates deployed one aircraft at a time
- No single point of failure — any aircraft can be grounded without losing
  the mission

## Design Implications

### Standardized Payload Bay

All aircraft carry the same mounting interface, power connector, and data bus.
Payload modules are self-contained units that plug into the bay:

- Standard dimensions and mass limit (sized to the per-aircraft payload budget)
- Power interface (DC bus at aircraft voltage)
- Data interface (Ethernet or similar for sensor data to the navigator)
- Quick-release mounting (tool-free swap in <30 minutes)

### Formation Size Trade

| Formation | Rotation viability | Why |
|---|---|---|
| N=2 | Poor | Losing 1 of 2 kills payload capacity entirely |
| N=3 | Marginal | 2-of-3 maintains payload but with significant drag penalty |
| N=4 | Good | 3-of-4 is the sweet spot — 14% drag penalty, 75% availability |
| N=6 | Excellent | 5-of-6 has only 8% drag penalty, 83% availability |

This analysis favors N=4-6 for missions requiring payload rotation,
which is also the range where $/kg payload flattens in the scaling analysis.

### Comparison to Single Aircraft

A single aircraft must carry all mission payloads simultaneously or land
to reconfigure. A formation with payload swap provides:

- **4x mission types per day** (vs 1 for single aircraft)
- **Zero coverage gaps** during reconfiguration
- **Battery swap extends seasonal envelope** beyond solar closure limits
- **Graceful degradation** — one aircraft failure is 25% capacity loss, not 100%
- **Independent maintenance** — no mission downtime for inspections
