# Hybrid Operations — Solo Day, Formation Night

## Concept

Aircraft fly independently during the day and form up at night.

- **Day (solo):** Each aircraft operates independently — spread out for sensor
  coverage, no station keeping power, no collision risk, simpler control. Solar
  panels collect energy for flight and battery charging.
- **Dusk transition (~30 min):** Aircraft rendezvous and establish formation.
- **Night (formation):** V-formation flight with wake vortex surfing reduces
  induced drag ~35%, extending battery endurance through the night.
- **Dawn transition (~30 min):** Formation disperses, aircraft resume solo ops.

## Why It Works

The 3× solar margin means panels are oversized for daytime power needs
regardless of flight mode. Whether solo or in formation during the day, the
aircraft collects excess energy. The formation drag benefit is irrelevant
during the day — there's more than enough solar power either way.

At night, formation drag reduction is critical. Without it, small aircraft
(6×15m) can't carry enough battery to survive the night. The wake benefit
is load-bearing for night survival, not a daytime optimization.

## Comparison (4×20m, 200W payload, 20km altitude, 30°N summer)

| Mode | Day power | Night power | Batt/ac | Panel area | Coverage |
|------|-----------|-------------|---------|------------|----------|
| Always formation | 1,302 W | 1,213 W | 12.2 kg | 20.4 m² | 10.6% |
| **Hybrid** | **1,550 W** | **1,213 W** | **12.2 kg** | **22.8 m²** | **11.9%** |
| Always solo | 2,863 W | 2,749 W | 27.7 kg | 45.5 m² | 23.7% |

### Key observations

- Hybrid night power and battery mass are **identical** to always-formation —
  the night phase is the same in both modes.
- Hybrid needs only **2.4 m² more panel** (+12% coverage) to cover the higher
  solo day power draw. Minimal cost impact.
- Always-solo requires **2.3× the battery** and **2× the panel area**. For
  6×15m, always-solo doesn't converge at all — the aircraft can't carry enough
  battery without formation drag reduction at night.

## Operational Advantages

**Better sensor coverage.** Solo aircraft can spread across a wide area during
the day. A 4-aircraft formation covers one point; 4 solo aircraft cover 4
independent tracks.

**Reduced risk.** No close-proximity flight during turbulent daytime hours.
The stratosphere is calm at night (turbulence intensity drops significantly),
making nighttime the safer window for formation flying.

**Simpler daytime control.** No station keeping, no relative navigation, no
wake tracking. Each aircraft runs its own autopilot independently.

**Graceful degradation.** If one aircraft has a station keeping failure, it
flies solo all night at higher power. It burns more battery but doesn't
endanger the formation. It can rejoin the next night if the issue is resolved.

## Transition Cost

Rendezvous at dusk and dispersal at dawn each take ~30 minutes for aircraft
within a reasonable operating radius. This is negligible compared to 10h of
nighttime formation and 14h of daytime solo ops. The energy cost of the
maneuver (slight speed/altitude changes during join-up) is small relative
to the 3× solar margin available at end of day.

## Design Implications

- **Battery sizing** is driven entirely by night formation power, same as
  always-formation mode.
- **Panel sizing** needs a small bump (+12% coverage) to account for higher
  solo day power, but this is minor — coverage goes from 10.6% to 11.9%
  on wings that could support up to 90%.
- **Station keeping hardware** is still needed but only active ~10h/day
  instead of 24h, reducing wear and failure probability.
- **Formation control software** only needs to be robust for calm nighttime
  stratospheric conditions, not turbulent daytime thermals.
