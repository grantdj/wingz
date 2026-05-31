# Operational Concepts — Formation Solar HALE

## 1. Hybrid Day/Night Operations

**Solo by day, formation at night.**

During the day, aircraft fly independently — spread out for wide-area
sensor coverage, no station keeping, no collision risk. The 3× solar
margin provides excess energy regardless of flight mode.

At dusk (~30 min), aircraft rendezvous and establish V-formation. Wake
vortex surfing reduces induced drag ~35%, cutting night power draw and
extending battery life. At dawn, formation disperses.

The formation drag benefit is load-bearing only at night. During the day,
it's irrelevant — there's 3× more solar energy than needed. This means
formation control software only needs to handle calm nighttime
stratospheric conditions, not turbulent daytime thermals.

See [hybrid_ops.md](hybrid_ops.md) for detailed analysis.

## 2. Sprint Transit — Use Excess Solar for Speed

The 3× solar margin means the panels produce roughly 3× more power than
needed for normal cruise. During transit, that excess power can drive the
aircraft at much higher speeds during daylight hours.

### Power Budget During Sprint

The solar panels must simultaneously:
1. Power the aircraft in flight
2. Charge batteries for the night

After reserving power for battery charging, the remaining solar budget is
available for propulsion. This is 4–5× the normal cruise power.

### Speed Analysis (4×20m, 200W payload)

| Phase | Speed | Power |
|---|---|---|
| Normal cruise (1.15× stall) | 13.0 m/s (25 kts) | 1,767 W |
| Night formation (1.03× stall) | 11.6 m/s (23 kts) | 1,213 W |
| **Day sprint (avg solar)** | **28.6 m/s (56 kts)** | **7,285 W** |
| Day sprint (peak, noon) | 34.3 m/s (67 kts) | ~13,000 W |

Sprint speed is **2.2× normal cruise**. The aircraft fly fast during the
day and slow at night. This increases the effective 24-hour average speed
by 1.7×.

### Transit Time: CONUS to Guam (9,630 km)

| Mode | 4×20m | 6×15m |
|---|---|---|
| Normal cruise (24h) | 8.6 days | 8.2 days |
| **Sprint (day fast, night slow)** | **5.2 days** | **4.9 days** |

With typical headwinds (10 m/s):

| Mode | 4×20m | 6×15m |
|---|---|---|
| Normal cruise | 17+ days | 17+ days |
| **Sprint** | **9.7 days** | **8.8 days** |

Sprint mode cuts transit time by 40% in zero wind and is even more
important in headwinds — the higher sprint speed maintains positive
ground speed against winds that would nearly stall a normal-cruise
aircraft.

### Why This Works

Drag power scales as V³ at high speed (parasite drag dominates). Doubling
speed requires roughly 8× the power. But the 3× solar margin provides
4–5× the propulsion budget during the day, which translates to ~2.2×
speed. The nonlinear drag penalty limits the speed gain, but the 14-hour
day window at summer solstice means most of the transit distance is
covered during the sprint phase.

### Operational Implications

**Pre-positioning on strategic warning.** A fleet of formation HALE
aircraft at a CONUS base (e.g., Edwards AFB) can self-deploy to Guam in
5–10 days on strategic warning. No airlift, no tankers, no overflight
permissions, no forward base agreements. The aircraft are their own
logistics.

**Phased deployment.** Launch one fleet per day for a week. By day 12,
you have 7 fleets on-station with the first already operational for
several days. Each fleet provides persistent ISR, comms relay, or PNT
over a different sector.

**Route optimization.** Transit routing through lower latitudes (longer
days, weaker headwinds) trades distance for speed. A great-circle route
from LAX to Guam passes through mid-latitude jet stream; a southern
routing via Hawaii adds ~15% distance but can halve headwind penalties.

## 3. Mothership Operations

Formation carries deployable small UAS (Switchblade 600, Altius-600
class) at 65,000 ft.

**Concept of operations:**
1. Formation loiters over area of interest for weeks/months
2. On command, designated aircraft deploys small UAS from altitude
3. Small UAS descend into denied airspace — 65kft gives enormous
   standoff; targets cannot intercept before the UAS reaches them
4. Formation continues mission with remaining aircraft
5. Resupply: replacement aircraft self-deploy from rear area and join

**Payload distribution example (4×20m):**

| Aircraft | Role | Payload |
|---|---|---|
| 1 (Leader) | ISR + formation lead | EO/IR sensor, 100W |
| 2 | Comms relay | SATCOM/LOS relay, 150W |
| 3 | Arsenal | 4× Switchblade 600, 50W standby |
| 4 | Arsenal | 4× Switchblade 600, 50W standby |

Lose aircraft 3 → aircraft 4 still has 4 munitions. Lose the comms
relay → degrade to LOS only. Lose the leader → another aircraft
assumes lead. Graceful degradation at every level.

## 4. Persistent PNT Source

Broadcast assured position/navigation/timing signals from 65,000 ft as
a GPS alternative in contested environments.

**Coverage:** A single aircraft at 65kft has a line-of-sight horizon
radius of ~300 nm (555 km). A formation of 4 aircraft spread during the
day covers ~1,200 nm of coastline or ~960,000 km² of ocean.

**Accuracy:** Airborne PNT from known position with precision clock can
provide meter-level accuracy to receivers within line of sight. Not as
good as GPS (centimeter), but far better than inertial drift in a GPS-
denied environment.

**Resilience:** The PNT source is mobile, hard to jam (directional
transmit from 65kft), and distributed across multiple aircraft. Destroying
it requires finding and killing each aircraft individually.

## 5. Comms Relay for JADC2

Line-of-sight communications relay from 65,000 ft.

**Problem:** In a Pacific conflict, SATCOM may be degraded by ASAT weapons.
Surface ships and ground forces need resilient beyond-line-of-sight comms.

**Solution:** Formation HALE at 65kft bridges the gap. Each aircraft is a
relay node with 300nm line-of-sight radius. A chain of formations across
the Pacific creates a persistent, mobile communications backbone that
doesn't depend on space assets.

**Topology:**
```
Guam ←300nm→ Formation A ←300nm→ Formation B ←300nm→ Fleet at sea
```

Three formations chain-link across 900nm of ocean with full duplex
data relay. If one formation is attacked, adjacent formations can
reposition to close the gap.

## 6. Electronic Warfare

Multiple small aircraft at 65,000 ft provide distributed EW capability.

**Advantages of distribution:**
- Multiple transmit points make the source hard to geolocate
- Wideband coverage from spatially separated platforms
- Redundancy — jamming one aircraft doesn't silence the formation
- Geometric diversity for direction-finding and SIGINT

## Summary: Operating Modes

| Mode | Day ops | Night ops | Use case |
|---|---|---|---|
| **Loiter** | Solo, spread | Formation | Persistent ISR, comms, PNT on-station |
| **Sprint transit** | Solo, max speed | Formation, min power | Self-deploy CONUS → theater |
| **Mothership** | Solo ISR + standby | Formation | Arsenal for attritable UAS |
| **Relay chain** | Formation (tight) | Formation | JADC2 comms backbone |
