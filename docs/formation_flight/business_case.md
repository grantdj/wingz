# Business Case — Formation Solar HALE

## DOD Strategic Alignment

The DOD's six critical technology areas (Emil Michael, Nov 2025) map
directly to this capability:

| DOD Priority | How Formation HALE Fits |
|---|---|
| **Applied AI** | Autonomous formation control, sensor fusion across distributed fleet |
| **Contested Logistics** | Self-deploying from CONUS, no forward basing, no fuel resupply |
| **Quantum & Battlefield Info Dominance (Q-BID)** | Persistent PNT source, comms relay, spectrum dominance from 65kft |
| **Scaled Directed Energy** | Not directly applicable (potential future: laser relay) |
| **Scaled Hypersonics** | Not applicable |
| **Biomanufacturing** | Not applicable |

Three of six priorities are direct hits. Q-BID is the strongest — the DOD
explicitly calls out PNT alternatives to GPS and comms in denied environments.

## Capability Overview

A fleet of 4–6 small (15–20m span) solar-powered aircraft flying in
formation at 65,000 ft. Indefinite endurance (months). Hybrid operations:
solo by day for distributed coverage, formation at night for battery
survival. Self-deploys from CONUS — no forward basing required.

### What it does

| Mission | How |
|---|---|
| **Persistent ISR** | EO/IR, SAR, SIGINT from 65kft — covers thousands of km² continuously |
| **Comms relay** | Line-of-sight relay for JADC2; 65kft horizon radius ~300 nm; replaces or augments degraded SATCOM |
| **PNT source** | Broadcast assured PNT signals as GPS alternative in contested/jammed environments |
| **Drone mothership** | Carry and deploy small UAS (Switchblade, Altius) from altitude into denied airspace |
| **Electronic warfare** | Distributed EW from multiple airborne nodes; hard to geolocate or jam |
| **Weapons platform** | Deploy guided munitions from 65kft; long standoff, hard to detect |

### What makes formation different

**Not a single large HALE.** A Zephyr or Skydweller is one $5–10M aircraft.
If it goes down, the mission is over. A formation of 4–6 small aircraft:

- **Costs 80% less** to manufacture (small wings, commodity autoclaves)
- **Degrades gracefully** — lose one aircraft, lose one sensor, not the mission
- **Distributes signatures** — 4 small aircraft are harder to target than 1 large one
- **Scales payload** — different aircraft carry different sensors/effectors
- **Self-deploys** — no C-5 required, no forward base, no runway

## Transit Analysis

Self-deployment from CONUS (West Coast) to Guam: ~5,200 nm (9,630 km).

The 3× solar margin enables a **sprint transit mode**: aircraft fly at
maximum speed during the day (using all excess solar power for
propulsion) and minimum speed at night in formation (conserving battery).
Day sprint speed is 2.2× normal cruise — 56 kts vs 25 kts for 4×20m.

| Config | Mode | No wind | 10 m/s headwind |
|---|---|---|---|
| 4×20m | Normal cruise | 8.6 days | 17+ days |
| 4×20m | **Sprint transit** | **5.2 days** | **9.7 days** |
| 6×15m | Normal cruise | 8.2 days | 17+ days |
| 6×15m | **Sprint transit** | **4.9 days** | **8.8 days** |

At 65,000 ft (stratosphere), winds are typically 10–30 m/s westerly at
mid-latitudes but weaken near the equator. Optimal routing south through
the tropics adds distance but avoids the worst headwinds. Realistic
sprint transit: **5–10 days** with weather-optimized routing.

For comparison:
- Sealift (cargo ship): 14–21 days
- Airlift (C-17): 1 day + forward base infrastructure
- Skydweller (single HALE): similar transit but $5–10M at risk in one airframe

**Pre-positioning without pre-positioning.** Aircraft can self-deploy on
strategic warning and be on-station over Guam in under a week — no bases,
no fuel, no logistics tail. Sprint transit is critical: it cuts 40% off
transit time vs normal cruise.

See [operational_concepts.md](operational_concepts.md) for detailed
sprint transit analysis.

## Defense Market

### Total Addressable Market

| Segment | Estimated TAM | Rationale |
|---|---|---|
| Persistent ISR (HALE) | $3–5B/yr | Replaces/augments Global Hawk ($130M/unit), MQ-9 in permissive environments |
| Comms relay (SATCOM alternative) | $2–4B/yr | JADC2 resilience; each combatant command needs distributed relay |
| PNT (GPS alternative) | $1–2B/yr | Q-BID priority; airborne PNT fills gap between GPS and inertial |
| Drone mothership | $1–3B/yr | Replicator/DAWG concept; forward deployment of attritable UAS |
| **Total defense TAM** | **$7–14B/yr** | |

### Key Programs to Target

**DAWG (Defense Autonomous Warfare Group):** $225M FY2026, $54.6B requested
FY2027. DAWG wants "orchestrator technologies" for autonomous swarms — a
formation HALE with mothership capability is exactly this.

**Pacific Deterrence Initiative (PDI):** $10B FY2026. Infrastructure
resilience and advanced technologies for Indo-Pacific. Formation HALE
eliminates the need for forward infrastructure.

**Replicator legacy:** DOD OIG found Replicator systems were "far too
expensive and slow to manufacture in the quantity needed." Formation HALE
using commodity-sized components directly addresses this finding.

**K1000ULE precedent:** Kraus Hamdani won up to $270M IDIQ for persistent
ISR in the Pacific. Their platform is 20ft span, 20kft altitude, 75hr
endurance. Formation solar HALE at 65kft with indefinite endurance is a
generational leap.

### Indo-Pacific Theater Fit

The Indo-Pacific is the defining use case:

- **Vast distances** — 5,000+ nm from CONUS to theater. Self-deploying
  aircraft eliminate airlift/sealift dependency.
- **Limited basing** — few friendly runways in the Western Pacific. Solar
  HALE needs no runway, no fuel, no ground infrastructure.
- **A2/AD environment** — PRC conventional missiles threaten fixed bases.
  A formation at 65kft, constantly moving, presents no fixed target.
- **SATCOM vulnerability** — Chinese ASAT capability threatens space-based
  comms. Airborne relay at 65kft provides resilient line-of-sight comms
  with 300nm horizon radius.
- **PNT denial** — GPS jamming is a day-one capability. Airborne PNT
  source provides assured navigation for forces in the first island chain.

**Specific scenarios:**
- **Taiwan contingency:** Formation loitering over the Philippine Sea
  provides ISR of the Taiwan Strait, comms relay for naval forces, and
  PNT for assets operating under GPS denial.
- **South China Sea:** Persistent maritime domain awareness without
  risking manned aircraft or surface ships.
- **Guam defense:** Integrated air defense sensor network augmentation.

### Mothership Concept

A formation of 4–6 aircraft at 65,000 ft carrying deployable small UAS:

1. Formation loiters over area of interest for weeks/months
2. On command, one or more aircraft deploy Switchblade 600 or Altius-600
   class munitions/ISR drones
3. Small UAS descend into denied airspace — impossible to intercept from
   the ground before reaching target
4. Formation continues mission with remaining aircraft
5. Resupply: replacement aircraft self-deploy from rear area, join formation

This is the "arsenal plane" concept applied to small attritable UAS,
with the mothership powered by the sun and stationed indefinitely.

### Survivability

Why a formation at 65kft is hard to kill:

- **Altitude:** Beyond effective range of MANPADS, most AAA, and many SAM
  systems. Requires dedicated high-altitude interceptors.
- **Small RCS:** 15–20m composite aircraft at 65kft have minimal radar
  cross-section. No metal, no jet exhaust, no fuel.
- **Distributed:** 4–6 aircraft spread across the sky. Killing one doesn't
  kill the mission. Shooting them all requires multiple engagements.
- **Replaceable:** At $200K–$1M per aircraft (at volume), they are
  attritable. Each shot costs the adversary more than the target.
- **No fixed base:** No runway to crater, no hangar to bomb, no fuel
  depot to destroy. The aircraft *are* the infrastructure.

## Commercial Market

### Addressable Segments

| Segment | Estimated TAM | Use case |
|---|---|---|
| Telecom relay (rural/disaster) | $1–2B/yr | Persistent connectivity where towers/satellites aren't viable |
| Environmental monitoring | $500M–1B/yr | Wildfire detection, weather, atmospheric science |
| Maritime surveillance | $500M–1B/yr | Fisheries enforcement, piracy, trafficking |
| Precision agriculture | $200–500M/yr | Large-area crop monitoring at high revisit rates |
| **Total commercial TAM** | **$2–5B/yr** | |

### Telecom Relay (Largest Commercial Opportunity)

Pseudo-satellite at 65kft with 300nm coverage radius. One formation
covers ~280,000 nm² — equivalent to a low-orbit satellite but without
the orbital mechanics, launch cost, or latency. Provides 4G/5G
connectivity to underserved areas.

Competitors: Loon (shut down), Airbus Zephyr (limited production),
Skydweller (single aircraft), HAPSMobile/SoftBank. None have a
cost-effective formation approach.

## Cost Advantage Summary

At production volume of 100 fleets (from our cost model):

| Config | Fleet cost | Per-aircraft | vs single 60m HALE |
|---|---|---|---|
| 1×60m | $5.24M | $5.24M | baseline |
| 4×20m | $1.13M | $283K | **78% cheaper** |
| 6×15m | $0.97M | $162K | **81% cheaper** |

Solar panels ($425–487K) dominate recurring cost. Manufacturing capital
(autoclave, tooling, factory) dominates at low volume and permanently
favors smaller aircraft — a 60m autoclave costs $176M vs $5.5M for 15m.

## Competitive Landscape

| Platform | Span | Endurance | Altitude | Unit cost | Status |
|---|---|---|---|---|---|
| Zephyr S (Airbus) | 25m | 30–60 days | 65kft | ~$6.5M | Limited production |
| Skydweller | 72m | 30–90 days | 45kft | ~$10M+ | Navy demo |
| Sunglider/Horus A (AV) | 78m | Months | 65kft | Unknown | Army testing |
| K1000ULE (KHA) | 6m | 75 hrs | 20kft | <$1M | AFCENT IDIQ $270M |
| Global Hawk (Northrop) | 40m | 34 hrs | 60kft | $130M | In service |
| **Formation HALE** | **4×20m** | **Indefinite** | **65kft** | **$1.1M fleet** | **Concept** |

Formation HALE is 5–100× cheaper than existing HALE platforms with
comparable or better endurance, and adds distributed resilience that
single-aircraft platforms fundamentally cannot provide.
