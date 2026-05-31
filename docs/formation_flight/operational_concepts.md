# Operational Concepts — Formation Solar HALE

## Core Concept

One aircraft, one battery, one night profile. Every day the aircraft
climbs to high altitude and every night it descends to denser air for
efficient formation flight. The only variable is what the aircraft does
with its daytime solar surplus:

- **Transit:** Dump it all into speed (sprint)
- **On-station:** Cruise gently, spread out for sensor coverage

There is no separate "dash mode" or "loiter mode" in the hardware. It's
the same aircraft, same battery, same altitude cycling. The autopilot
simply chooses speed vs coverage based on mission phase.

## Daily Altitude Cycle

The aircraft always cycles altitude — climb by day, descend by night.
This is fundamental to the energy balance, not an optional optimization.

```
22km ──────────┐                    ┌──────────
  Day: sprint  │    Dusk descent    │  Day: sprint
  or cruise    │         ↓          │  or cruise
               │                    │
15-18km        └────────────────────┘
                Night: formation
                slow, dense air
                gravity-assisted
```

**Why cycle:**
- **Night at lower altitude** — denser air means lower stall speed,
  lower power to stay aloft, smaller battery. Flying at 15km vs 22km
  at night cuts battery mass by 60%.
- **Gravity assist** — descending 4–7 km converts potential energy into
  flight time. At 22km→15km, this provides ~190W of free power all
  night, directly reducing battery drain.
- **Day at high altitude** — better solar irradiance (thinner atmosphere),
  higher true airspeed for the same indicated airspeed (faster sprint).
- **Climb cost is paid by solar** — climbing back up in the morning
  costs energy, but there's 3× solar margin to cover it.

### Altitude Cycling Analysis (4×20m, 200W payload)

| Profile | Batt/ac | Night speed | Sprint speed | Guam transit |
|---|---|---|---|---|
| Fixed 20km | 14.5 kg | 11.6 m/s | 28.7 m/s | 5.2 days |
| Fixed 22km | 20.6 kg | 14.8 m/s | 36.1 m/s | 4.1 days |
| **22km / 18km cycle** | **8.5 kg** | **9.0 m/s** | **30.1 m/s** | **5.2 days** |
| 22km / 15km cycle | 4.8 kg | 6.7 m/s | 28.0 m/s | 5.9 days |
| 20km / 15km cycle | 5.8 kg | 6.8 m/s | 24.7 m/s | 6.5 days |

The **22km/18km cycle** is the sweet spot: same transit time as fixed
20km (5.2 days) but with **40% less battery** (8.5 vs 14.5 kg). Lighter
aircraft, less structure, less cost.

## Daytime Operations

### Transit (Sprint)

During transit, all excess solar power goes to propulsion. The aircraft
sprint solo at 2.2× cruise speed during the day, then form up and slow
down at night.

**Power budget during sprint:**

The solar panels simultaneously:
1. Power the aircraft at sprint speed
2. Charge batteries for the night
3. Power the climb back to day altitude

After reserving for batteries and climb, the remaining 4–5× normal
cruise power drives the aircraft at ~30 m/s (58 kts) vs ~13 m/s
(25 kts) normal cruise.

**Transit time: CONUS to Guam (9,630 km, 22km/18km cycling)**

| Conditions | 4×20m | 6×15m |
|---|---|---|
| No wind | 5.2 days | 4.9 days |
| 10 m/s headwind | ~10 days | ~9 days |

Sprint is critical against headwinds. At normal cruise (13 m/s), a
10 m/s headwind leaves only 3 m/s ground speed — the transit balloons
to weeks. At sprint (30 m/s), the same headwind leaves 20 m/s — still
making real progress.

**Formation doesn't help sprint speed.** At sprint speed, parasite drag
is 94% of total drag. Formation wake surfing only reduces induced drag
(the other 6%). The sprint speed gain from formation is +1% — negligible.
Aircraft fly solo during the day regardless.

### On-Station (Loiter)

On-station, the aircraft cruise at minimum power and spread out for
sensor coverage. The excess solar power goes unused (or powers payload
at higher duty cycle).

**Day formation is unnecessary on-station.** The 3× solar margin means
energy balance closes easily whether solo or in formation. Solo
operations provide:
- Wide-area sensor coverage (4 aircraft, 4 separate tracks)
- No collision risk during turbulent daytime hours
- No station keeping power draw
- Simpler control (each aircraft runs independently)

## Nighttime Operations

Every night, regardless of mission phase:

1. **Dusk (~30 min):** Aircraft descend from day altitude and rendezvous
   into V-formation
2. **Night (10 hours):** Formation flight at 1.03× stall speed in dense
   air. Wake vortex surfing reduces induced drag ~35%. Gravity assist
   from continued gentle descent provides free power.
3. **Dawn (~30 min):** Formation disperses, aircraft climb back to day
   altitude and resume solo ops

**Why formation matters at night:**
- At low speed, induced drag is 50–60% of total drag — the formation
  benefit is real and load-bearing
- Without formation, 6×15m aircraft can't survive the night at all
  (mass doesn't converge — can't carry enough battery)
- Stratosphere is calm at night — ideal conditions for precision
  formation flying

**Station keeping is servo power, not thrust.** The control surfaces
make continuous micro-corrections (4 servos, ~4–9W total). Motor thrust
stays at trim. See station_keeping.py for the model.

## Mission Profiles

### Persistent ISR

- Day: Solo at 22km, spread for wide-area coverage, EO/IR/SAR/SIGINT
- Night: Formation at 15–18km, maintaining coverage over primary target
- Endurance: Indefinite (months)

### Comms Relay (JADC2)

Line-of-sight relay from 65kft. Each aircraft provides 300nm coverage
radius. A chain of formations bridges the Pacific without SATCOM.

```
Guam ←300nm→ Formation A ←300nm→ Formation B ←300nm→ Fleet at sea
```

### PNT Source

Broadcast assured PNT signals as GPS alternative in denied environments.
4 aircraft spread during the day cover ~1,200 nm of coastline. At night,
formation maintains coverage over the primary operating area.

### Mothership

Carry and deploy small UAS (Switchblade 600, Altius-600) from 65kft.
Deploy on command, continue mission with remaining aircraft.

| Aircraft | Role | Payload |
|---|---|---|
| 1 (Leader) | ISR + formation lead | EO/IR sensor, 100W |
| 2 | Comms relay | SATCOM/LOS relay, 150W |
| 3 | Arsenal | 4× Switchblade 600, 50W standby |
| 4 | Arsenal | 4× Switchblade 600, 50W standby |

### Electronic Warfare

Distributed EW from multiple airborne nodes. Multiple transmit points
are hard to geolocate, hard to jam. Geometric diversity enables
direction-finding and SIGINT.

## Summary

| Phase | Altitude | Speed | Formation | Power use |
|---|---|---|---|---|
| **Day transit** | 22km (climb) | Sprint (30 m/s) | Solo | All excess → speed |
| **Day on-station** | 22km (climb) | Cruise (13 m/s) | Solo, spread | Excess unused / payload |
| **Night (always)** | 15–18km (descend) | Min power (9 m/s) | V-formation | Battery + gravity assist |

One aircraft. One battery. One night profile. Sprint or loiter is just
a throttle setting.
