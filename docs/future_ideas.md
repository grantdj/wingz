# Future Ideas

Ideas to investigate once core modeling is established.

## Power Transfer Between Vehicles

In a heterogeneous formation, aircraft have different power-to-weight ratios.
The light front-runners have excess solar capacity relative to their drag;
the heavy navigator in the wake has more payload mass competing for panel area.
Sharing power across the formation could let the fleet optimize collectively.

### Tethering

Physical cables between aircraft for power transfer. Tethers add drag,
constrain formation geometry, and create failure modes (tangling, snap loads
in turbulence). At 20 km in thin air, tether drag could be significant
relative to the small forces involved. Worth modeling if power sharing
proves valuable — start with a simple model of tether drag penalty vs.
power transfer benefit.

### Wireless Power Transfer

Microwave or laser power beaming between aircraft. No physical connection,
but efficiency losses and pointing requirements. May be more practical at
the power levels involved (tens to hundreds of watts). Very speculative.

## Analytical Beam Model

Euler-Bernoulli spar sizing with real carbon fiber layup properties. Build once
empirical results identify promising design regions.

## CFD Validation

Higher-fidelity formation aerodynamics if classical Hummel/Lissaman results
prove insufficient for the spacing regimes we care about.

## Dynamic Simulation

Time-domain formation control simulation — gust response, station-keeping
dynamics, failure recovery.
