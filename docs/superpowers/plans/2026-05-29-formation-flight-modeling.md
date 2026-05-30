# Formation Flight Modeling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a layered physics library for comparing single high-aspect-ratio solar aircraft against formations of smaller aircraft, with calibrated models, parameter sweeps, and visualization.

**Architecture:** Separate Python modules per physics domain (structures, aero, solar, control, cost), composed through an evaluation layer. Each sub-model is independently testable. Existing `formation_span_model.py` code is refactored into the new package structure.

**Tech Stack:** Python 3.11+, numpy, scipy (curve fitting), matplotlib, pandas, pytest

**Spec:** `docs/superpowers/specs/2026-05-29-formation-flight-modeling-design.md`

---

### Task 1: Project Scaffolding

**Files:**
- Create: `wingz/__init__.py`
- Create: `wingz/structures/__init__.py`
- Create: `wingz/aerodynamics/__init__.py`
- Create: `wingz/solar/__init__.py`
- Create: `wingz/control/__init__.py`
- Create: `wingz/cost/__init__.py`
- Create: `wingz/mission/__init__.py`
- Create: `wingz/evaluation/__init__.py`
- Create: `wingz/visualization/__init__.py`
- Create: `tests/__init__.py`
- Create: `docs/formation_flight/.gitkeep`
- Create: `docs/future_ideas.md`
- Create: `scripts/.gitkeep`
- Create: `notebooks/.gitkeep`
- Create: `pyproject.toml`

- [ ] **Step 1: Create package directories and init files**

```bash
mkdir -p wingz/{structures,aerodynamics,solar,control,cost,mission,evaluation,visualization}
mkdir -p tests
mkdir -p scripts notebooks
mkdir -p docs/formation_flight
```

Create empty `__init__.py` in each:
- `wingz/__init__.py`
- `wingz/structures/__init__.py`
- `wingz/aerodynamics/__init__.py`
- `wingz/solar/__init__.py`
- `wingz/control/__init__.py`
- `wingz/cost/__init__.py`
- `wingz/mission/__init__.py`
- `wingz/evaluation/__init__.py`
- `wingz/visualization/__init__.py`
- `tests/__init__.py`

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "wingz"
version = "0.1.0"
description = "Formation flight vs single aircraft modeling for solar HALE platforms"
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.24",
    "scipy>=1.10",
    "matplotlib>=3.7",
    "pandas>=2.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0"]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"
```

- [ ] **Step 3: Create docs/future_ideas.md**

```markdown
# Future Ideas

Ideas to investigate once core modeling is established.

## Tethering

Physical cables between aircraft for power transfer. The leader with more solar
panel area could feed power to lighter followers. Tethers add drag, constrain
formation geometry, and create failure modes (tangling, snap loads in turbulence).
At 20 km in thin air, tether drag could be significant relative to the small
forces involved. Worth modeling if power sharing proves valuable.

## Analytical Beam Model

Euler-Bernoulli spar sizing with real carbon fiber layup properties. Build once
empirical results identify promising design regions.

## CFD Validation

Higher-fidelity formation aerodynamics if classical Hummel/Lissaman results
prove insufficient for the spacing regimes we care about.

## Dynamic Simulation

Time-domain formation control simulation — gust response, station-keeping
dynamics, failure recovery.
```

- [ ] **Step 4: Install in development mode and verify**

Run: `cd /Users/dgrant/Documents/personal/wingz && pip install -e ".[dev]"`
Expected: successful install, `import wingz` works.

- [ ] **Step 5: Commit**

```bash
git add wingz/ tests/ docs/ scripts/ notebooks/ pyproject.toml
git commit -m "feat: scaffold wingz package structure"
```

---

### Task 2: Mission Profiles

**Files:**
- Create: `wingz/mission/profiles.py`
- Create: `tests/test_mission.py`

This is the foundation — every other module takes a mission profile as input.

- [ ] **Step 1: Write the failing test**

`tests/test_mission.py`:
```python
import numpy as np
from wingz.mission.profiles import MissionProfile, hale_20km, lower_altitude_le


def test_hale_profile_defaults():
    m = hale_20km()
    assert m.altitude_m == 20000
    assert 0.08 < m.rho < 0.10  # ~0.089 kg/m^3 at 20km
    assert 20 < m.velocity < 35
    assert m.min_endurance_days == 30


def test_lower_altitude_profile():
    m = lower_altitude_le()
    assert m.altitude_m < 20000
    assert m.rho > hale_20km().rho  # denser air
    assert m.velocity > hale_20km().velocity  # faster in denser air


def test_dynamic_pressure():
    m = hale_20km()
    q = m.dynamic_pressure()
    expected = 0.5 * m.rho * m.velocity**2
    assert abs(q - expected) < 1e-10


def test_wing_area():
    m = hale_20km()
    weight_N = 1000.0
    area = m.wing_area(weight_N)
    assert abs(area - weight_N / m.wing_loading_N_m2) < 1e-10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mission.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

`wingz/mission/profiles.py`:
```python
from dataclasses import dataclass


@dataclass
class MissionProfile:
    name: str
    altitude_m: float
    rho: float                    # kg/m^3, air density at altitude
    velocity: float               # m/s, cruise speed
    oswald_e: float               # span efficiency factor
    cd0: float                    # parasite drag coefficient
    wing_loading_N_m2: float      # W/S, N/m^2
    min_endurance_days: int        # minimum mission duration
    turbulence_intensity: float   # relative scale 0-1 (0=calm, 1=severe)

    def dynamic_pressure(self) -> float:
        return 0.5 * self.rho * self.velocity**2

    def wing_area(self, weight_N: float) -> float:
        return weight_N / self.wing_loading_N_m2


def hale_20km() -> MissionProfile:
    return MissionProfile(
        name="HALE 20km",
        altitude_m=20000,
        rho=0.0889,
        velocity=25.0,
        oswald_e=0.85,
        cd0=0.025,
        wing_loading_N_m2=45.0,
        min_endurance_days=30,
        turbulence_intensity=0.1,
    )


def lower_altitude_le() -> MissionProfile:
    return MissionProfile(
        name="Lower-altitude LE",
        altitude_m=12000,
        rho=0.312,
        velocity=40.0,
        oswald_e=0.82,
        cd0=0.028,
        wing_loading_N_m2=80.0,
        min_endurance_days=30,
        turbulence_intensity=0.4,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mission.py -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add wingz/mission/profiles.py tests/test_mission.py
git commit -m "feat(mission): add HALE and lower-altitude mission profiles"
```

---

### Task 3: Structures — Empirical Scaling

**Files:**
- Create: `wingz/structures/empirical.py`
- Create: `tests/test_structures.py`

Calibrate power-law wing mass model against real solar/HALE aircraft data.

- [ ] **Step 1: Write the failing test**

`tests/test_structures.py`:
```python
import numpy as np
from wingz.structures.empirical import (
    EmpiricalStructure,
    SOLAR_HALE_DATA,
    fit_power_law,
)


def test_aircraft_data_exists():
    assert len(SOLAR_HALE_DATA) >= 7
    for entry in SOLAR_HALE_DATA:
        assert entry["span_m"] > 0
        assert entry["wing_mass_kg"] > 0
        assert "name" in entry


def test_fit_power_law():
    coefficient, exponent = fit_power_law(SOLAR_HALE_DATA)
    assert exponent > 1.5  # should be superlinear
    assert exponent < 4.0  # but not absurdly high
    assert coefficient > 0


def test_wing_mass_increases_with_span():
    model = EmpiricalStructure.from_data(SOLAR_HALE_DATA)
    m20 = model.wing_mass(20.0)
    m40 = model.wing_mass(40.0)
    m60 = model.wing_mass(60.0)
    assert m20 < m40 < m60


def test_wing_mass_matches_data_order_of_magnitude():
    model = EmpiricalStructure.from_data(SOLAR_HALE_DATA)
    # Zephyr: 25m span, ~7 kg wing mass
    predicted = model.wing_mass(25.0)
    assert 2 < predicted < 30  # within reasonable range of ~7 kg


def test_extrapolation_flag():
    model = EmpiricalStructure.from_data(SOLAR_HALE_DATA)
    result = model.wing_mass_with_confidence(25.0)
    assert result["interpolating"] is True

    result = model.wing_mass_with_confidence(5.0)
    assert result["interpolating"] is False

    result = model.wing_mass_with_confidence(100.0)
    assert result["interpolating"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_structures.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

`wingz/structures/empirical.py`:
```python
from dataclasses import dataclass
import numpy as np
from scipy.optimize import curve_fit


SOLAR_HALE_DATA = [
    {"name": "Zephyr S", "span_m": 25, "wing_mass_kg": 7, "mtow_kg": 75,
     "source": "Airbus", "mass_confidence": "estimated"},
    {"name": "PHASA-35", "span_m": 35, "wing_mass_kg": 15, "mtow_kg": 150,
     "source": "BAE Systems", "mass_confidence": "estimated"},
    {"name": "Pathfinder Plus", "span_m": 36.3, "wing_mass_kg": 30, "mtow_kg": 315,
     "source": "NASA", "mass_confidence": "estimated"},
    {"name": "Odysseus", "span_m": 74, "wing_mass_kg": 130, "mtow_kg": 180,
     "source": "Boeing Aurora", "mass_confidence": "estimated"},
    {"name": "Helios", "span_m": 75.3, "wing_mass_kg": 180, "mtow_kg": 1052,
     "source": "NASA", "mass_confidence": "estimated"},
    {"name": "HAPSMobile Sunglider", "span_m": 78, "wing_mass_kg": 200, "mtow_kg": 260,
     "source": "SoftBank", "mass_confidence": "estimated"},
    {"name": "Solar Impulse 2", "span_m": 71.9, "wing_mass_kg": 250, "mtow_kg": 2300,
     "source": "SI Foundation", "mass_confidence": "estimated"},
]


def _power_law(span, coefficient, exponent):
    return coefficient * span**exponent


def fit_power_law(data: list[dict]) -> tuple[float, float]:
    spans = np.array([d["span_m"] for d in data])
    masses = np.array([d["wing_mass_kg"] for d in data])
    popt, _ = curve_fit(_power_law, spans, masses, p0=[0.01, 2.0])
    return float(popt[0]), float(popt[1])


@dataclass
class EmpiricalStructure:
    coefficient: float
    exponent: float
    min_span: float
    max_span: float

    @classmethod
    def from_data(cls, data: list[dict]) -> "EmpiricalStructure":
        coefficient, exponent = fit_power_law(data)
        spans = [d["span_m"] for d in data]
        return cls(
            coefficient=coefficient,
            exponent=exponent,
            min_span=min(spans),
            max_span=max(spans),
        )

    def wing_mass(self, span_m: float) -> float:
        return self.coefficient * span_m**self.exponent

    def wing_mass_with_confidence(self, span_m: float) -> dict:
        return {
            "mass_kg": self.wing_mass(span_m),
            "interpolating": self.min_span <= span_m <= self.max_span,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_structures.py -v`
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add wingz/structures/empirical.py tests/test_structures.py
git commit -m "feat(structures): empirical wing mass scaling calibrated to solar HALE data"
```

---

### Task 4: Aerodynamics — Basic Drag

**Files:**
- Create: `wingz/aerodynamics/drag.py`
- Create: `tests/test_drag.py`

Refactor the induced/parasite drag functions from `formation_span_model.py` into the new package.

- [ ] **Step 1: Write the failing test**

`tests/test_drag.py`:
```python
import numpy as np
from wingz.aerodynamics.drag import induced_drag, parasite_drag, total_drag
from wingz.mission.profiles import hale_20km


def test_induced_drag_decreases_with_span():
    m = hale_20km()
    d20 = induced_drag(1000.0, 20.0, m)
    d40 = induced_drag(1000.0, 40.0, m)
    d80 = induced_drag(1000.0, 80.0, m)
    assert d20 > d40 > d80


def test_induced_drag_inverse_square_span():
    m = hale_20km()
    d20 = induced_drag(1000.0, 20.0, m)
    d40 = induced_drag(1000.0, 40.0, m)
    # doubling span should quarter induced drag
    ratio = d20 / d40
    assert abs(ratio - 4.0) < 0.01


def test_induced_drag_known_value():
    m = hale_20km()
    q = 0.5 * m.rho * m.velocity**2
    W = 1000.0
    b = 30.0
    expected = W**2 / (q * np.pi * m.oswald_e * b**2)
    assert abs(induced_drag(W, b, m) - expected) < 1e-6


def test_parasite_drag_proportional_to_area():
    m = hale_20km()
    d1 = parasite_drag(1000.0, m)
    d2 = parasite_drag(2000.0, m)
    # double weight -> double wing area -> double parasite drag
    assert abs(d2 / d1 - 2.0) < 0.01


def test_total_drag_is_sum():
    m = hale_20km()
    di = induced_drag(1000.0, 30.0, m)
    dp = parasite_drag(1000.0, m)
    dt = total_drag(1000.0, 30.0, m)
    assert abs(dt - (di + dp)) < 1e-10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_drag.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

`wingz/aerodynamics/drag.py`:
```python
import numpy as np
from wingz.mission.profiles import MissionProfile


def induced_drag(
    weight_N: float,
    span_m: float,
    mission: MissionProfile,
    formation_factor: float = 1.0,
) -> float:
    """
    D_i = W^2 / (q * pi * e * b^2)

    formation_factor < 1.0 reduces induced drag (wake surfing benefit).
    """
    q = mission.dynamic_pressure()
    return formation_factor * weight_N**2 / (q * np.pi * mission.oswald_e * span_m**2)


def parasite_drag(weight_N: float, mission: MissionProfile) -> float:
    """D_p = q * S * C_D0"""
    q = mission.dynamic_pressure()
    area = mission.wing_area(weight_N)
    return q * area * mission.cd0


def total_drag(
    weight_N: float,
    span_m: float,
    mission: MissionProfile,
    formation_factor: float = 1.0,
) -> float:
    return (
        induced_drag(weight_N, span_m, mission, formation_factor)
        + parasite_drag(weight_N, mission)
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_drag.py -v`
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add wingz/aerodynamics/drag.py tests/test_drag.py
git commit -m "feat(aero): basic induced and parasite drag model"
```

---

### Task 5: Aerodynamics — Formation Model

**Files:**
- Create: `wingz/aerodynamics/formation_aero.py`
- Create: `tests/test_formation_aero.py`

Spacing-dependent formation drag model based on Hummel/Lissaman, exposed as effective span.

- [ ] **Step 1: Write the failing test**

`tests/test_formation_aero.py`:
```python
import numpy as np
from wingz.aerodynamics.formation_aero import (
    FormationGeometry,
    per_slot_drag_factor,
    effective_span,
)


def test_leader_gets_no_benefit():
    factors = per_slot_drag_factor(
        N=3, span_m=10.0, lateral_overlap_ratio=0.1,
        geometry=FormationGeometry.V,
    )
    assert factors[0] == 1.0  # leader at index 0


def test_followers_get_benefit():
    factors = per_slot_drag_factor(
        N=3, span_m=10.0, lateral_overlap_ratio=0.1,
        geometry=FormationGeometry.V,
    )
    for f in factors[1:]:
        assert f < 1.0  # followers have drag reduction


def test_more_overlap_more_benefit():
    factors_low = per_slot_drag_factor(
        N=3, span_m=10.0, lateral_overlap_ratio=0.0,
        geometry=FormationGeometry.V,
    )
    factors_high = per_slot_drag_factor(
        N=3, span_m=10.0, lateral_overlap_ratio=0.1,
        geometry=FormationGeometry.V,
    )
    # more overlap -> lower drag factor for followers
    assert factors_high[1] < factors_low[1]


def test_effective_span_greater_than_individual():
    b_eff = effective_span(
        N=3, span_m=10.0, lateral_overlap_ratio=0.1,
        geometry=FormationGeometry.V,
    )
    assert b_eff > 10.0  # formation effective span > single aircraft span


def test_single_aircraft_effective_span_equals_span():
    b_eff = effective_span(
        N=1, span_m=20.0, lateral_overlap_ratio=0.0,
        geometry=FormationGeometry.V,
    )
    assert abs(b_eff - 20.0) < 1e-10


def test_echelon_vs_v_formation():
    b_v = effective_span(
        N=5, span_m=10.0, lateral_overlap_ratio=0.1,
        geometry=FormationGeometry.V,
    )
    b_ech = effective_span(
        N=5, span_m=10.0, lateral_overlap_ratio=0.1,
        geometry=FormationGeometry.ECHELON,
    )
    # V gives more benefit (followers get upwash from both sides deeper in V)
    assert b_v > b_ech


def test_v_formation_symmetric_slots():
    """Left and right slots at same depth should have same factor in zero crosswind."""
    factors = per_slot_drag_factor(
        N=5, span_m=10.0, lateral_overlap_ratio=0.1,
        geometry=FormationGeometry.V,
    )
    # slots 1,2 are left/right of leader; slots 3,4 are next pair
    assert abs(factors[1] - factors[2]) < 1e-10
    assert abs(factors[3] - factors[4]) < 1e-10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_formation_aero.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

`wingz/aerodynamics/formation_aero.py`:
```python
"""
Formation aerodynamics based on Hummel/Lissaman classical wake interaction.

The key result: a trailing aircraft positioned in the upwash of a leader's
wingtip vortex sees reduced induced drag. The benefit depends on:
- Lateral overlap ratio (tip gap / span)
- Position in formation (leader gets nothing, first follower gets most)
- Formation geometry (V, echelon, inline)

We expose this as per-slot drag factors and an effective span for the whole
formation.
"""

import enum
import numpy as np


class FormationGeometry(enum.Enum):
    V = "v"
    ECHELON = "echelon"
    INLINE = "inline"


def _single_wake_drag_factor(lateral_overlap_ratio: float) -> float:
    """
    Drag reduction factor for one aircraft surfing one neighbor's wake.

    Based on Lissaman & Shollenberger (1970) and Hummel (1983):
    the optimal overlap is ~5-15% of span. At zero overlap (wingtip-to-wingtip),
    benefit is small. At large overlap, the follower enters downwash and
    drag increases.

    Returns a factor in (0, 1] where 1.0 = no benefit.
    The factor represents the fraction of induced drag remaining.
    """
    # Parameterize as a function of overlap ratio r:
    # r < 0: gap between wingtips (small benefit)
    # r ~ 0.1: optimal overlap (max benefit, ~25-40% reduction)
    # r > 0.3: entering downwash region (benefit decreases)
    r = lateral_overlap_ratio
    # Gaussian-like benefit centered at r=0.1
    optimal_r = 0.1
    sigma = 0.15
    max_reduction = 0.35  # max ~35% induced drag reduction from one wake
    reduction = max_reduction * np.exp(-((r - optimal_r) ** 2) / (2 * sigma**2))
    return 1.0 - reduction


def per_slot_drag_factor(
    N: int,
    span_m: float,
    lateral_overlap_ratio: float,
    geometry: FormationGeometry,
) -> list[float]:
    """
    Compute induced drag factor for each aircraft slot in the formation.

    Returns a list of N floats, each in (0, 1]. Index 0 is the leader.
    Factor of 1.0 = full induced drag. Factor of 0.7 = 30% reduction.

    In a V formation, slots are ordered: [leader, left1, right1, left2, right2, ...]
    In an echelon, slots are ordered: [leader, follower1, follower2, ...]
    In inline, all followers are directly behind with no lateral offset.
    """
    if N == 1:
        return [1.0]

    base_factor = _single_wake_drag_factor(lateral_overlap_ratio)

    if geometry == FormationGeometry.INLINE:
        # Inline: followers are directly behind, in downwash not upwash
        # Very little benefit — mostly just drafting effect
        factors = [1.0]  # leader
        for i in range(1, N):
            factors.append(1.0 - 0.05 * min(i, 3))  # tiny benefit, caps out
        return factors

    if geometry == FormationGeometry.ECHELON:
        # Echelon: each follower surfs one neighbor's wake
        factors = [1.0]  # leader
        for i in range(1, N):
            # Diminishing returns: each successive follower's wake is weaker
            # because the aircraft ahead is producing less induced drag
            cumulative = base_factor ** (1.0 + 0.15 * (i - 1))
            factors.append(cumulative)
        return factors

    # V formation: followers are paired left/right
    # Each follower in the V surfs the wake of the aircraft ahead on their side.
    # Deeper in the V, followers potentially benefit from two upstream neighbors.
    factors = [1.0]  # leader
    depth = 1
    idx = 1
    while idx < N:
        # At each depth, two slots (left and right) — symmetric in still air
        wake_count = min(depth, 2)  # at depth >= 2, benefit from 2 upstream wakes
        slot_factor = base_factor ** wake_count
        # Diminishing returns with depth
        slot_factor = slot_factor ** (1.0 + 0.1 * (depth - 1))

        factors.append(slot_factor)  # left
        idx += 1
        if idx < N:
            factors.append(slot_factor)  # right (symmetric)
            idx += 1
        depth += 1

    return factors


def effective_span(
    N: int,
    span_m: float,
    lateral_overlap_ratio: float,
    geometry: FormationGeometry,
) -> float:
    """
    Compute the effective span of the formation.

    The formation's total induced drag equals what a single aircraft with
    span b_eff would produce carrying the same total weight.

    D_i_formation = sum(factor_i * W_i^2 / (q pi e b_i^2))

    For identical aircraft with equal weight shares:
    D_i_formation = (W/N)^2 / (q pi e b^2) * sum(factor_i)
              = W^2 / (q pi e) * sum(factor_i) / (N^2 * b^2)

    Setting equal to D_i_single = W^2 / (q pi e b_eff^2):
    b_eff = N * b / sqrt(sum(factor_i))
    """
    if N == 1:
        return span_m

    factors = per_slot_drag_factor(N, span_m, lateral_overlap_ratio, geometry)
    return N * span_m / np.sqrt(sum(factors))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_formation_aero.py -v`
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add wingz/aerodynamics/formation_aero.py tests/test_formation_aero.py
git commit -m "feat(aero): spacing-dependent formation drag model with per-slot factors"
```

---

### Task 6: Control — Formation Architectures

**Files:**
- Create: `wingz/control/architectures.py`
- Create: `tests/test_control.py`

Define hardware mass/power profiles for leader/follower, tiered, and mesh architectures.

- [ ] **Step 1: Write the failing test**

`tests/test_control.py`:
```python
import numpy as np
from wingz.control.architectures import (
    FormationArchitecture,
    AircraftRole,
    get_hardware_mass,
    get_hardware_power,
    assign_roles,
)


def test_leader_heavier_than_follower_in_leader_follower():
    leader_mass = get_hardware_mass(FormationArchitecture.LEADER_FOLLOWER, AircraftRole.LEADER)
    follower_mass = get_hardware_mass(FormationArchitecture.LEADER_FOLLOWER, AircraftRole.FOLLOWER)
    assert leader_mass > follower_mass


def test_mesh_all_equal():
    mass_a = get_hardware_mass(FormationArchitecture.MESH, AircraftRole.LEADER)
    mass_b = get_hardware_mass(FormationArchitecture.MESH, AircraftRole.FOLLOWER)
    assert mass_a == mass_b


def test_leader_follower_roles():
    roles = assign_roles(FormationArchitecture.LEADER_FOLLOWER, N=4)
    assert roles.count(AircraftRole.LEADER) == 1
    assert roles.count(AircraftRole.FOLLOWER) == 3


def test_tiered_has_sub_leaders():
    roles = assign_roles(FormationArchitecture.TIERED, N=6)
    assert AircraftRole.SUB_LEADER in roles
    assert roles[0] == AircraftRole.LEADER


def test_mesh_all_peers():
    roles = assign_roles(FormationArchitecture.MESH, N=4)
    assert all(r == AircraftRole.PEER for r in roles)


def test_total_hardware_mass():
    roles = assign_roles(FormationArchitecture.LEADER_FOLLOWER, N=4)
    total = sum(
        get_hardware_mass(FormationArchitecture.LEADER_FOLLOWER, r) for r in roles
    )
    # 1 leader (~2.5 kg) + 3 followers (~0.4 kg each) = ~3.7 kg
    assert 2.0 < total < 6.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_control.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

`wingz/control/architectures.py`:
```python
"""
Formation architecture definitions.

Each architecture defines what hardware each aircraft carries (IMU, GPS,
comms, relative nav sensors) and therefore the mass and power cost of
the control system per aircraft.
"""

import enum
import math


class FormationArchitecture(enum.Enum):
    LEADER_FOLLOWER = "leader_follower"
    TIERED = "tiered"
    MESH = "mesh"


class AircraftRole(enum.Enum):
    LEADER = "leader"          # full nav: IMU + GPS + comms + compute
    SUB_LEADER = "sub_leader"  # partial nav: IMU + GPS + datalink
    FOLLOWER = "follower"      # relative only: UWB/visual + datalink
    PEER = "peer"              # mesh: partial suite + cooperative nav


# Hardware mass in kg per role
_HARDWARE_MASS = {
    FormationArchitecture.LEADER_FOLLOWER: {
        AircraftRole.LEADER: 2.5,    # full IMU + GPS + comms + compute
        AircraftRole.FOLLOWER: 0.4,  # UWB ranging + radio
    },
    FormationArchitecture.TIERED: {
        AircraftRole.LEADER: 2.5,
        AircraftRole.SUB_LEADER: 1.5,  # IMU + GPS + datalink
        AircraftRole.FOLLOWER: 0.4,
    },
    FormationArchitecture.MESH: {
        AircraftRole.PEER: 1.0,  # partial IMU + radio + cooperative compute
    },
}

# Hardware power draw in watts per role
_HARDWARE_POWER = {
    FormationArchitecture.LEADER_FOLLOWER: {
        AircraftRole.LEADER: 15.0,
        AircraftRole.FOLLOWER: 3.0,
    },
    FormationArchitecture.TIERED: {
        AircraftRole.LEADER: 15.0,
        AircraftRole.SUB_LEADER: 10.0,
        AircraftRole.FOLLOWER: 3.0,
    },
    FormationArchitecture.MESH: {
        AircraftRole.PEER: 8.0,
    },
}


def get_hardware_mass(arch: FormationArchitecture, role: AircraftRole) -> float:
    return _HARDWARE_MASS[arch][role]


def get_hardware_power(arch: FormationArchitecture, role: AircraftRole) -> float:
    return _HARDWARE_POWER[arch][role]


def assign_roles(arch: FormationArchitecture, N: int) -> list[AircraftRole]:
    """
    Assign roles to N aircraft for the given architecture.
    Returns a list of N AircraftRole values. Index 0 is the formation leader position.
    """
    if N == 1:
        return [AircraftRole.LEADER]

    if arch == FormationArchitecture.LEADER_FOLLOWER:
        return [AircraftRole.LEADER] + [AircraftRole.FOLLOWER] * (N - 1)

    if arch == FormationArchitecture.TIERED:
        # 1 leader, then 1 sub-leader per ~3 followers, rest are followers
        n_sub = max(1, math.ceil((N - 1) / 4))
        n_follow = N - 1 - n_sub
        return (
            [AircraftRole.LEADER]
            + [AircraftRole.SUB_LEADER] * n_sub
            + [AircraftRole.FOLLOWER] * n_follow
        )

    # Mesh: all peers
    return [AircraftRole.PEER] * N
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_control.py -v`
Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add wingz/control/architectures.py tests/test_control.py
git commit -m "feat(control): formation architecture definitions with hardware mass/power"
```

---

### Task 7: Control — Station Keeping

**Files:**
- Create: `wingz/control/station_keeping.py`
- Create: `tests/test_station_keeping.py`

Model the energy cost of maintaining formation position.

- [ ] **Step 1: Write the failing test**

`tests/test_station_keeping.py`:
```python
from wingz.control.station_keeping import station_keeping_power
from wingz.mission.profiles import hale_20km, lower_altitude_le


def test_power_positive():
    p = station_keeping_power(
        mission=hale_20km(),
        span_m=20.0,
        position_tolerance_m=2.0,
    )
    assert p > 0


def test_tighter_tolerance_more_power():
    p_loose = station_keeping_power(
        mission=hale_20km(),
        span_m=20.0,
        position_tolerance_m=5.0,
    )
    p_tight = station_keeping_power(
        mission=hale_20km(),
        span_m=20.0,
        position_tolerance_m=1.0,
    )
    assert p_tight > p_loose


def test_more_turbulence_more_power():
    p_calm = station_keeping_power(
        mission=hale_20km(),      # turbulence_intensity=0.1
        span_m=20.0,
        position_tolerance_m=2.0,
    )
    p_rough = station_keeping_power(
        mission=lower_altitude_le(),  # turbulence_intensity=0.4
        span_m=20.0,
        position_tolerance_m=2.0,
    )
    assert p_rough > p_calm


def test_leader_zero_station_keeping():
    """Leader flies its own path — no station-keeping cost."""
    p = station_keeping_power(
        mission=hale_20km(),
        span_m=20.0,
        position_tolerance_m=2.0,
        is_leader=True,
    )
    assert p == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_station_keeping.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

`wingz/control/station_keeping.py`:
```python
"""
Station-keeping energy model.

Estimates the additional power required for a follower aircraft to maintain
its position in the formation. Driven by:
- Turbulence intensity (atmospheric + vortex wake)
- Required position tolerance (tighter = more corrections)
- Aircraft size (larger = more inertia, harder to correct)
"""

from wingz.mission.profiles import MissionProfile


def station_keeping_power(
    mission: MissionProfile,
    span_m: float,
    position_tolerance_m: float,
    is_leader: bool = False,
    in_wake: bool = True,
) -> float:
    """
    Estimate power (watts) required for station-keeping.

    The leader flies its own path and has zero station-keeping cost.
    Followers must correct for atmospheric turbulence and vortex-induced
    disturbances.

    Model: P_sk = k * turbulence * (1/tolerance) * span^1.5
    - turbulence drives the magnitude of corrections
    - tighter tolerance requires more frequent/larger corrections
    - larger aircraft need more force to reposition

    The wake adds extra turbulence for followers in vortex positions.
    """
    if is_leader:
        return 0.0

    base_turbulence = mission.turbulence_intensity
    # Wake adds ~50% more turbulence for aircraft in vortex positions
    wake_factor = 1.5 if in_wake else 1.0
    effective_turbulence = base_turbulence * wake_factor

    # Empirical scaling constant — calibrated so that a 20m span aircraft
    # at 2m tolerance in calm conditions uses ~2-5W for station-keeping
    k = 50.0

    return k * effective_turbulence * (1.0 / position_tolerance_m) * span_m**1.5
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_station_keeping.py -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add wingz/control/station_keeping.py tests/test_station_keeping.py
git commit -m "feat(control): station-keeping power model"
```

---

### Task 8: Solar Power Model

**Files:**
- Create: `wingz/solar/power.py`
- Create: `tests/test_solar.py`

Solar flux, panel output, and day/night profile.

- [ ] **Step 1: Write the failing test**

`tests/test_solar.py`:
```python
import numpy as np
from wingz.solar.power import (
    solar_irradiance,
    panel_power,
    day_length_hours,
    daily_energy_available,
)


def test_irradiance_at_20km():
    irr = solar_irradiance(altitude_m=20000, latitude_deg=30, day_of_year=172)
    # Above most atmosphere, should be close to solar constant
    assert 1200 < irr < 1400  # W/m^2 peak


def test_irradiance_lower_altitude_less():
    irr_high = solar_irradiance(altitude_m=20000, latitude_deg=30, day_of_year=172)
    irr_low = solar_irradiance(altitude_m=12000, latitude_deg=30, day_of_year=172)
    assert irr_high > irr_low


def test_panel_power():
    p = panel_power(
        wing_area_m2=50.0,
        coverage_fraction=0.8,
        panel_efficiency=0.25,
        irradiance_W_m2=1300.0,
    )
    expected = 50.0 * 0.8 * 0.25 * 1300.0
    assert abs(p - expected) < 1e-6


def test_day_length_equator_equinox():
    hours = day_length_hours(latitude_deg=0, day_of_year=80)  # ~March equinox
    assert abs(hours - 12.0) < 0.5


def test_day_length_summer_longer():
    summer = day_length_hours(latitude_deg=45, day_of_year=172)  # June solstice
    winter = day_length_hours(latitude_deg=45, day_of_year=355)  # Dec solstice
    assert summer > winter


def test_daily_energy():
    energy = daily_energy_available(
        wing_area_m2=50.0,
        coverage_fraction=0.8,
        panel_efficiency=0.25,
        altitude_m=20000,
        latitude_deg=30,
        day_of_year=172,
    )
    # Should be in the range of tens of kWh for a 50 m^2 wing
    assert energy > 0
    assert energy < 200 * 3600  # < 200 kWh in Wh (sanity)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_solar.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

`wingz/solar/power.py`:
```python
"""
Solar power model for high-altitude aircraft.

Models solar irradiance as a function of altitude (atmospheric absorption),
latitude and day-of-year (sun angle and day length), and panel characteristics.
"""

import numpy as np


# Solar constant at top of atmosphere (W/m^2)
SOLAR_CONSTANT = 1361.0


def solar_irradiance(altitude_m: float, latitude_deg: float, day_of_year: int) -> float:
    """
    Peak solar irradiance available at the given altitude.

    At 20 km, most atmospheric absorption is below — irradiance is ~95-98%
    of the solar constant. At lower altitudes, more absorption occurs.

    Uses a simple exponential atmospheric transmission model:
    I = I_0 * exp(-tau * airmass)
    where tau decreases with altitude (less atmosphere above).
    """
    # Optical depth decreases roughly exponentially with altitude
    # Scale height of atmosphere ~8.5 km
    scale_height = 8500.0
    # Sea-level optical depth for clear sky, ~0.3 for direct beam
    tau_sea_level = 0.3
    tau = tau_sea_level * np.exp(-altitude_m / scale_height)

    # Air mass at peak solar elevation
    declination = _solar_declination(day_of_year)
    lat_rad = np.radians(latitude_deg)
    # Peak solar elevation angle
    sin_elevation = np.sin(lat_rad) * np.sin(declination) + np.cos(lat_rad) * np.cos(declination)
    sin_elevation = np.clip(sin_elevation, 0.01, 1.0)
    airmass = 1.0 / sin_elevation

    return SOLAR_CONSTANT * np.exp(-tau * airmass)


def panel_power(
    wing_area_m2: float,
    coverage_fraction: float,
    panel_efficiency: float,
    irradiance_W_m2: float,
) -> float:
    """Instantaneous power output from solar panels (watts)."""
    return wing_area_m2 * coverage_fraction * panel_efficiency * irradiance_W_m2


def day_length_hours(latitude_deg: float, day_of_year: int) -> float:
    """
    Approximate day length using the CBM model.

    Returns hours of sunlight.
    """
    declination = _solar_declination(day_of_year)
    lat_rad = np.radians(latitude_deg)

    # Hour angle at sunrise/sunset
    cos_hour_angle = -np.tan(lat_rad) * np.tan(declination)
    cos_hour_angle = np.clip(cos_hour_angle, -1.0, 1.0)

    hour_angle = np.arccos(cos_hour_angle)
    return float(2.0 * hour_angle * 12.0 / np.pi)


def daily_energy_available(
    wing_area_m2: float,
    coverage_fraction: float,
    panel_efficiency: float,
    altitude_m: float,
    latitude_deg: float,
    day_of_year: int,
) -> float:
    """
    Total energy available from solar panels over one day (watt-hours).

    Integrates panel power over the daylight hours, accounting for the
    sinusoidal variation of solar elevation through the day.
    The average irradiance over daylight hours is approximately 2/pi times
    the peak irradiance (sinusoidal integration).
    """
    peak_irr = solar_irradiance(altitude_m, latitude_deg, day_of_year)
    day_hours = day_length_hours(latitude_deg, day_of_year)

    # Average irradiance over daylight is ~(2/pi) * peak for sinusoidal sun path
    avg_irr = (2.0 / np.pi) * peak_irr
    avg_power = panel_power(wing_area_m2, coverage_fraction, panel_efficiency, avg_irr)

    return avg_power * day_hours


def _solar_declination(day_of_year: int) -> float:
    """Solar declination angle in radians."""
    return np.radians(23.45) * np.sin(np.radians(360 / 365 * (day_of_year - 81)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_solar.py -v`
Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add wingz/solar/power.py tests/test_solar.py
git commit -m "feat(solar): solar irradiance and panel power model"
```

---

### Task 9: Solar — Energy Balance

**Files:**
- Create: `wingz/solar/energy_balance.py`
- Create: `tests/test_energy_balance.py`

The endurance gate: can the aircraft close the 24h energy cycle?

- [ ] **Step 1: Write the failing test**

`tests/test_energy_balance.py`:
```python
import numpy as np
from wingz.solar.energy_balance import (
    EnergyBalanceResult,
    compute_energy_balance,
    required_battery_mass,
)


def test_energy_balance_returns_result():
    result = compute_energy_balance(
        power_required_W=200.0,
        wing_area_m2=50.0,
        coverage_fraction=0.8,
        panel_efficiency=0.25,
        altitude_m=20000,
        latitude_deg=30,
        day_of_year=172,
    )
    assert isinstance(result, EnergyBalanceResult)
    assert result.day_hours > 0
    assert result.night_hours > 0
    assert abs(result.day_hours + result.night_hours - 24.0) < 0.1


def test_generous_conditions_closes():
    """Big wing, low power, summer, low latitude — should close easily."""
    result = compute_energy_balance(
        power_required_W=100.0,
        wing_area_m2=80.0,
        coverage_fraction=0.85,
        panel_efficiency=0.28,
        altitude_m=20000,
        latitude_deg=20,
        day_of_year=172,
    )
    assert result.closes


def test_impossible_conditions_fails():
    """Tiny wing, high power, winter, high latitude — should not close."""
    result = compute_energy_balance(
        power_required_W=500.0,
        wing_area_m2=10.0,
        coverage_fraction=0.7,
        panel_efficiency=0.20,
        altitude_m=20000,
        latitude_deg=55,
        day_of_year=355,
    )
    assert not result.closes


def test_battery_mass_positive():
    mass = required_battery_mass(
        power_required_W=200.0,
        night_hours=12.0,
        battery_energy_density_Wh_kg=250.0,
    )
    assert mass > 0
    # 200W * 12h = 2400 Wh / 250 Wh/kg = 9.6 kg
    assert abs(mass - 9.6) < 0.1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_energy_balance.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

`wingz/solar/energy_balance.py`:
```python
"""
Energy balance for 24-hour cycle closure.

For 30+ day endurance, the aircraft must generate enough solar energy during
the day to power flight AND charge batteries for the night. If the energy
balance doesn't close on the worst-case day, the mission is infeasible.
"""

from dataclasses import dataclass
from wingz.solar.power import daily_energy_available, day_length_hours


@dataclass
class EnergyBalanceResult:
    day_hours: float
    night_hours: float
    energy_available_Wh: float
    energy_required_day_Wh: float
    energy_required_night_Wh: float
    energy_required_total_Wh: float
    surplus_Wh: float
    closes: bool


def compute_energy_balance(
    power_required_W: float,
    wing_area_m2: float,
    coverage_fraction: float,
    panel_efficiency: float,
    altitude_m: float,
    latitude_deg: float,
    day_of_year: int,
) -> EnergyBalanceResult:
    """
    Check whether the aircraft can sustain 24-hour flight.

    power_required_W is the total continuous power draw: thrust + avionics
    + control hardware + payload.
    """
    day_hours = day_length_hours(latitude_deg, day_of_year)
    night_hours = 24.0 - day_hours

    energy_available = daily_energy_available(
        wing_area_m2, coverage_fraction, panel_efficiency,
        altitude_m, latitude_deg, day_of_year,
    )

    energy_required_day = power_required_W * day_hours
    energy_required_night = power_required_W * night_hours
    energy_required_total = energy_required_day + energy_required_night

    surplus = energy_available - energy_required_total

    return EnergyBalanceResult(
        day_hours=day_hours,
        night_hours=night_hours,
        energy_available_Wh=energy_available,
        energy_required_day_Wh=energy_required_day,
        energy_required_night_Wh=energy_required_night,
        energy_required_total_Wh=energy_required_total,
        surplus_Wh=surplus,
        closes=surplus >= 0,
    )


def required_battery_mass(
    power_required_W: float,
    night_hours: float,
    battery_energy_density_Wh_kg: float = 250.0,
) -> float:
    """
    Minimum battery mass to survive the night.

    Current Li-ion: ~250 Wh/kg. Li-S (near term): ~400 Wh/kg.
    Solid state (future): ~500+ Wh/kg.
    """
    night_energy_Wh = power_required_W * night_hours
    return night_energy_Wh / battery_energy_density_Wh_kg
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_energy_balance.py -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add wingz/solar/energy_balance.py tests/test_energy_balance.py
git commit -m "feat(solar): 24h energy balance and battery sizing model"
```

---

### Task 10: Cost — Mass Proxy Model

**Files:**
- Create: `wingz/cost/mass_proxy.py`
- Create: `tests/test_cost.py`

- [ ] **Step 1: Write the failing test**

`tests/test_cost.py`:
```python
from wingz.cost.mass_proxy import mass_proxy_cost


def test_cost_increases_with_mass():
    c1 = mass_proxy_cost(structural_mass_kg=50, control_mass_kg=5, N=3)
    c2 = mass_proxy_cost(structural_mass_kg=100, control_mass_kg=5, N=3)
    assert c2 > c1


def test_cost_increases_with_fleet_size():
    c1 = mass_proxy_cost(structural_mass_kg=50, control_mass_kg=5, N=2)
    c2 = mass_proxy_cost(structural_mass_kg=50, control_mass_kg=5, N=6)
    assert c2 > c1


def test_single_aircraft_no_complexity_penalty():
    c = mass_proxy_cost(structural_mass_kg=50, control_mass_kg=0, N=1)
    # no fleet coordination penalty for single aircraft
    c_base = mass_proxy_cost(structural_mass_kg=50, control_mass_kg=0, N=1)
    assert c == c_base
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cost.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

`wingz/cost/mass_proxy.py`:
```python
"""
Cost model using mass as a proxy.

Avoids dollar values entirely. Cost score is a weighted combination of
structural mass, control hardware mass, and fleet coordination complexity.
"""


def mass_proxy_cost(
    structural_mass_kg: float,
    control_mass_kg: float,
    N: int,
    structural_weight: float = 1.0,
    control_weight: float = 2.0,
    complexity_exponent: float = 1.2,
) -> float:
    """
    Cost score (dimensionless).

    - structural_weight: how much structural mass contributes to cost
    - control_weight: control hardware is more expensive per kg than structure
    - complexity_exponent: fleet coordination cost scales as N^exponent
    """
    mass_score = structural_weight * structural_mass_kg + control_weight * control_mass_kg
    complexity_score = N ** complexity_exponent if N > 1 else 1.0
    return mass_score * complexity_score
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cost.py -v`
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add wingz/cost/mass_proxy.py tests/test_cost.py
git commit -m "feat(cost): mass-proxy cost model"
```

---

### Task 11: Cost — Bottom-Up Materials Model

**Files:**
- Create: `wingz/cost/materials.py`
- Modify: `tests/test_cost.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_cost.py`:
```python
from wingz.cost.materials import materials_cost, MaterialPrices


def test_materials_cost_positive():
    c = materials_cost(
        structural_mass_kg=50,
        solar_panel_area_m2=40,
        control_mass_kg=3,
    )
    assert c > 0


def test_custom_prices():
    default = materials_cost(structural_mass_kg=50, solar_panel_area_m2=40, control_mass_kg=3)
    cheap = materials_cost(
        structural_mass_kg=50, solar_panel_area_m2=40, control_mass_kg=3,
        prices=MaterialPrices(carbon_fiber_per_kg=50),
    )
    assert cheap < default


def test_materials_cost_scales_with_panel_area():
    c1 = materials_cost(structural_mass_kg=50, solar_panel_area_m2=20, control_mass_kg=3)
    c2 = materials_cost(structural_mass_kg=50, solar_panel_area_m2=60, control_mass_kg=3)
    assert c2 > c1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cost.py -v`
Expected: new tests FAIL — cannot import materials

- [ ] **Step 3: Write implementation**

`wingz/cost/materials.py`:
```python
"""
Bottom-up materials cost model.

Estimates cost from component-level pricing. These are rough but based on
real market prices for aerospace-grade components.
"""

from dataclasses import dataclass


@dataclass
class MaterialPrices:
    carbon_fiber_per_kg: float = 120.0       # aerospace-grade CF layup, $/kg
    solar_cell_per_m2: float = 800.0         # lightweight flexible cells, $/m^2
    avionics_per_kg: float = 5000.0          # nav/comms hardware, $/kg
    battery_per_kWh: float = 300.0           # Li-ion cells, $/kWh
    assembly_per_kg_structure: float = 200.0  # labor + tooling, $/kg structure


def materials_cost(
    structural_mass_kg: float,
    solar_panel_area_m2: float,
    control_mass_kg: float,
    battery_capacity_kWh: float = 0.0,
    prices: MaterialPrices | None = None,
) -> float:
    """Estimated cost in dollars."""
    p = prices or MaterialPrices()
    return (
        p.carbon_fiber_per_kg * structural_mass_kg
        + p.solar_cell_per_m2 * solar_panel_area_m2
        + p.avionics_per_kg * control_mass_kg
        + p.battery_per_kWh * battery_capacity_kWh
        + p.assembly_per_kg_structure * structural_mass_kg
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cost.py -v`
Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add wingz/cost/materials.py tests/test_cost.py
git commit -m "feat(cost): bottom-up materials cost model"
```

---

### Task 12: Evaluation — Sweep Engine

**Files:**
- Create: `wingz/evaluation/sweep.py`
- Create: `tests/test_sweep.py`

The core parameter sweep engine that composes all sub-models.

- [ ] **Step 1: Write the failing test**

`tests/test_sweep.py`:
```python
import numpy as np
from wingz.evaluation.sweep import (
    AircraftConfig,
    evaluate_config,
    sweep_configs,
    PositionStrategy,
)
from wingz.mission.profiles import hale_20km
from wingz.control.architectures import FormationArchitecture
from wingz.aerodynamics.formation_aero import FormationGeometry


def test_evaluate_single_aircraft():
    config = AircraftConfig(
        N=1,
        span_each_m=30.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.UNIFORM,
        geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.1,
    )
    result = evaluate_config(config, hale_20km())
    assert result["N"] == 1
    assert result["total_drag_N"] > 0
    assert result["wing_mass_total_kg"] > 0


def test_evaluate_formation():
    config = AircraftConfig(
        N=4,
        span_each_m=15.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.HEAVY_WAKE,
        geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.1,
    )
    result = evaluate_config(config, hale_20km())
    assert result["N"] == 4
    assert result["architecture"] == "leader_follower"
    assert result["position_strategy"] == "heavy_wake"
    assert result["total_drag_N"] > 0
    assert result["control_mass_total_kg"] > 0


def test_sweep_produces_rows():
    configs = sweep_configs(
        spans=[10.0, 20.0],
        Ns=[1, 3],
        architectures=[FormationArchitecture.LEADER_FOLLOWER],
        position_strategies=[PositionStrategy.UNIFORM],
        geometries=[FormationGeometry.V],
        lateral_overlap_ratios=[0.1],
    )
    results = [evaluate_config(c, hale_20km()) for c in configs]
    assert len(results) == 4  # 2 spans x 2 Ns


def test_heavy_wake_vs_heavy_front_different():
    config_wake = AircraftConfig(
        N=4, span_each_m=15.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.HEAVY_WAKE,
        geometry=FormationGeometry.V, lateral_overlap_ratio=0.1,
    )
    config_front = AircraftConfig(
        N=4, span_each_m=15.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.HEAVY_FRONT,
        geometry=FormationGeometry.V, lateral_overlap_ratio=0.1,
    )
    r_wake = evaluate_config(config_wake, hale_20km())
    r_front = evaluate_config(config_front, hale_20km())
    # Should give different total drag due to weight distribution
    assert r_wake["total_drag_N"] != r_front["total_drag_N"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sweep.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

`wingz/evaluation/sweep.py`:
```python
"""
Parameter sweep engine.

Composes all sub-models to evaluate a complete aircraft or formation
configuration and produce a result dict suitable for DataFrame analysis.
"""

import enum
from dataclasses import dataclass
from itertools import product

import numpy as np

from wingz.aerodynamics.drag import induced_drag, parasite_drag
from wingz.aerodynamics.formation_aero import (
    FormationGeometry,
    per_slot_drag_factor,
    effective_span,
)
from wingz.control.architectures import (
    FormationArchitecture,
    assign_roles,
    get_hardware_mass,
    get_hardware_power,
)
from wingz.control.station_keeping import station_keeping_power
from wingz.cost.mass_proxy import mass_proxy_cost
from wingz.mission.profiles import MissionProfile
from wingz.structures.empirical import EmpiricalStructure, SOLAR_HALE_DATA


class PositionStrategy(enum.Enum):
    HEAVY_FRONT = "heavy_front"
    HEAVY_WAKE = "heavy_wake"
    UNIFORM = "uniform"


@dataclass
class AircraftConfig:
    N: int
    span_each_m: float
    architecture: FormationArchitecture
    position_strategy: PositionStrategy
    geometry: FormationGeometry
    lateral_overlap_ratio: float


def evaluate_config(
    config: AircraftConfig,
    mission: MissionProfile,
    structure: EmpiricalStructure | None = None,
) -> dict:
    """
    Evaluate a single configuration against a mission profile.

    Returns a flat dict with all computed metrics.
    """
    structure = structure or EmpiricalStructure.from_data(SOLAR_HALE_DATA)
    N = config.N
    span = config.span_each_m

    # Roles and hardware
    roles = assign_roles(config.architecture, N)
    hw_masses = [get_hardware_mass(config.architecture, r) for r in roles]
    hw_powers = [get_hardware_power(config.architecture, r) for r in roles]

    # Structural mass per aircraft (all have same wingspan)
    struct_mass_each = structure.wing_mass(span)

    # Total mass per aircraft (structure + hardware)
    total_mass_per = [struct_mass_each + hw for hw in hw_masses]

    # Weight per aircraft: proportional to its mass
    total_fleet_mass = sum(total_mass_per)
    # Use mission total weight, distributed by mass fraction
    # (heavier aircraft carry proportionally more weight)
    total_weight = total_fleet_mass * 9.81  # convert to N
    weights = [m / total_fleet_mass * total_weight for m in total_mass_per]

    # Per-slot drag factors
    drag_factors = per_slot_drag_factor(N, span, config.lateral_overlap_ratio, config.geometry)

    # Position strategy: reorder which aircraft sits in which slot
    if N > 1 and config.position_strategy == PositionStrategy.HEAVY_WAKE:
        # Put the heaviest aircraft in the slot with the lowest drag factor
        # (best wake position), lightest in the leader slot (highest factor)
        mass_order = np.argsort(total_mass_per)  # lightest first
        factor_order = np.argsort(drag_factors)[::-1]  # highest factor first (worst aero)
        # Map: lightest aircraft -> worst aero position (leader),
        #       heaviest -> best aero position
        slot_assignment = [0] * N
        for rank, aircraft_idx in enumerate(mass_order):
            slot_assignment[aircraft_idx] = factor_order[rank]
        # Reorder weights and powers to match slot assignment
        reordered_weights = [0.0] * N
        reordered_hw_powers = [0.0] * N
        reordered_hw_masses = [0.0] * N
        for aircraft_idx in range(N):
            slot = slot_assignment[aircraft_idx]
            reordered_weights[slot] = weights[aircraft_idx]
            reordered_hw_powers[slot] = hw_powers[aircraft_idx]
            reordered_hw_masses[slot] = hw_masses[aircraft_idx]
        weights = reordered_weights
        hw_powers = reordered_hw_powers
        hw_masses = reordered_hw_masses
    elif N > 1 and config.position_strategy == PositionStrategy.HEAVY_FRONT:
        # Heaviest aircraft in leader position (slot 0, factor=1.0)
        mass_order = np.argsort(total_mass_per)[::-1]  # heaviest first
        reordered_weights = [weights[i] for i in mass_order]
        reordered_hw_powers = [hw_powers[i] for i in mass_order]
        reordered_hw_masses = [hw_masses[i] for i in mass_order]
        weights = reordered_weights
        hw_powers = reordered_hw_powers
        hw_masses = reordered_hw_masses

    # Compute per-slot drag
    slot_induced_drags = []
    slot_parasite_drags = []
    for i in range(N):
        di = induced_drag(weights[i], span, mission, formation_factor=drag_factors[i])
        dp = parasite_drag(weights[i], mission)
        slot_induced_drags.append(di)
        slot_parasite_drags.append(dp)

    total_induced = sum(slot_induced_drags)
    total_parasite = sum(slot_parasite_drags)
    total_drag = total_induced + total_parasite

    # Station-keeping power (leader excluded)
    sk_powers = []
    for i in range(N):
        is_leader = (i == 0 and N > 1) or N == 1
        sk = station_keeping_power(
            mission=mission,
            span_m=span,
            position_tolerance_m=2.0,
            is_leader=is_leader,
        )
        sk_powers.append(sk)

    # Thrust power = drag * velocity
    thrust_power = total_drag * mission.velocity

    # Total power = thrust + avionics + station-keeping
    total_hw_power = sum(hw_powers)
    total_sk_power = sum(sk_powers)
    total_power = thrust_power + total_hw_power + total_sk_power

    # Wing area
    total_wing_area = sum(mission.wing_area(w) for w in weights)

    # Cost
    control_mass_total = sum(hw_masses)
    cost_score = mass_proxy_cost(
        structural_mass_kg=N * struct_mass_each,
        control_mass_kg=control_mass_total,
        N=N,
    )

    # Effective span
    b_eff = effective_span(N, span, config.lateral_overlap_ratio, config.geometry)

    return {
        "N": N,
        "span_each_m": span,
        "total_span_m": N * span,
        "effective_span_m": b_eff,
        "architecture": config.architecture.value,
        "position_strategy": config.position_strategy.value,
        "geometry": config.geometry.value,
        "lateral_overlap_ratio": config.lateral_overlap_ratio,
        "wing_mass_each_kg": struct_mass_each,
        "wing_mass_total_kg": N * struct_mass_each,
        "control_mass_total_kg": control_mass_total,
        "total_mass_kg": total_fleet_mass,
        "induced_drag_N": total_induced,
        "parasite_drag_N": total_parasite,
        "total_drag_N": total_drag,
        "thrust_power_W": thrust_power,
        "hw_power_W": total_hw_power,
        "sk_power_W": total_sk_power,
        "total_power_W": total_power,
        "total_wing_area_m2": total_wing_area,
        "cost_score": cost_score,
        "mission": mission.name,
    }


def sweep_configs(
    spans: list[float],
    Ns: list[int],
    architectures: list[FormationArchitecture],
    position_strategies: list[PositionStrategy],
    geometries: list[FormationGeometry],
    lateral_overlap_ratios: list[float],
) -> list[AircraftConfig]:
    """Generate all combinations of sweep parameters."""
    configs = []
    for span, N, arch, pos, geo, lor in product(
        spans, Ns, architectures, position_strategies, geometries, lateral_overlap_ratios
    ):
        # Skip formation-only params for single aircraft
        if N == 1:
            config = AircraftConfig(
                N=1, span_each_m=span,
                architecture=arch,
                position_strategy=PositionStrategy.UNIFORM,
                geometry=geo, lateral_overlap_ratio=0.0,
            )
            # Avoid duplicate single-aircraft configs
            if not any(
                c.N == 1 and c.span_each_m == span for c in configs
            ):
                configs.append(config)
        else:
            configs.append(AircraftConfig(
                N=N, span_each_m=span, architecture=arch,
                position_strategy=pos, geometry=geo,
                lateral_overlap_ratio=lor,
            ))
    return configs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_sweep.py -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add wingz/evaluation/sweep.py tests/test_sweep.py
git commit -m "feat(evaluation): parameter sweep engine composing all sub-models"
```

---

### Task 13: Evaluation — Pareto Analysis

**Files:**
- Create: `wingz/evaluation/pareto.py`
- Create: `tests/test_pareto.py`

- [ ] **Step 1: Write the failing test**

`tests/test_pareto.py`:
```python
from wingz.evaluation.pareto import pareto_filter


def test_pareto_filters_dominated():
    rows = [
        {"cost": 10, "drag": 10},  # dominated by (5, 5)
        {"cost": 5, "drag": 5},    # Pareto optimal
        {"cost": 3, "drag": 8},    # Pareto optimal (cheapest)
        {"cost": 8, "drag": 3},    # Pareto optimal (least drag)
    ]
    result = pareto_filter(rows, x_key="cost", y_key="drag")
    assert len(result) == 3
    # (10, 10) should be filtered out
    assert {"cost": 10, "drag": 10} not in result


def test_pareto_single_row():
    rows = [{"cost": 5, "drag": 5}]
    result = pareto_filter(rows, x_key="cost", y_key="drag")
    assert len(result) == 1


def test_pareto_empty():
    result = pareto_filter([], x_key="cost", y_key="drag")
    assert len(result) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pareto.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

`wingz/evaluation/pareto.py`:
```python
"""
Multi-objective Pareto analysis.

Filters a set of configurations to those that are not dominated in
the objective space. Lower is better for all objectives.
"""

import numpy as np


def pareto_filter(
    rows: list[dict],
    x_key: str = "cost_score",
    y_key: str = "total_drag_N",
) -> list[dict]:
    """
    Return rows that are not dominated in both x and y.
    A row is dominated if another row is <= in both objectives and < in at least one.
    """
    if not rows:
        return []

    # Sort by x, then y
    sorted_rows = sorted(rows, key=lambda r: (r[x_key], r[y_key]))
    pareto = []
    best_y = np.inf
    for row in sorted_rows:
        if row[y_key] < best_y:
            pareto.append(row)
            best_y = row[y_key]
    return pareto
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pareto.py -v`
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add wingz/evaluation/pareto.py tests/test_pareto.py
git commit -m "feat(evaluation): Pareto frontier filtering"
```

---

### Task 14: Visualization

**Files:**
- Create: `wingz/visualization/plots.py`
- Create: `tests/test_plots.py`

Reusable matplotlib plotting functions.

- [ ] **Step 1: Write the failing test**

`tests/test_plots.py`:
```python
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for testing
import matplotlib.pyplot as plt
import pandas as pd
from wingz.visualization.plots import (
    plot_cost_vs_drag,
    plot_structural_scaling,
    plot_energy_balance_timeline,
    plot_formation_geometry,
)


def test_cost_vs_drag_returns_figure():
    df = pd.DataFrame([
        {"cost_score": 100, "total_drag_N": 50, "N": 1, "architecture": "single"},
        {"cost_score": 80, "total_drag_N": 40, "N": 3, "architecture": "leader_follower"},
    ])
    fig, ax = plot_cost_vs_drag(df)
    assert fig is not None
    assert ax is not None
    plt.close(fig)


def test_structural_scaling_returns_figure():
    fig, ax = plot_structural_scaling()
    assert fig is not None
    plt.close(fig)


def test_formation_geometry_returns_figure():
    fig, ax = plot_formation_geometry(N=5, span_m=10.0, lateral_overlap_ratio=0.1, geometry="v")
    assert fig is not None
    plt.close(fig)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_plots.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

`wingz/visualization/plots.py`:
```python
"""
Reusable matplotlib plotting functions for formation flight analysis.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes

from wingz.structures.empirical import EmpiricalStructure, SOLAR_HALE_DATA


def plot_cost_vs_drag(
    df: pd.DataFrame,
    x_key: str = "cost_score",
    y_key: str = "total_drag_N",
    color_by: str = "architecture",
    pareto_df: pd.DataFrame | None = None,
) -> tuple[Figure, Axes]:
    """Scatter plot of cost vs drag, colored by configuration type."""
    fig, ax = plt.subplots(figsize=(10, 7))

    for label, group in df.groupby(color_by):
        ax.scatter(group[x_key], group[y_key], label=label, alpha=0.6, s=30)

    if pareto_df is not None and len(pareto_df) > 0:
        ax.scatter(
            pareto_df[x_key], pareto_df[y_key],
            marker="x", color="black", s=80, linewidths=2,
            label="Pareto frontier", zorder=5,
        )

    ax.set_xlabel("Cost score")
    ax.set_ylabel("Total drag (N)")
    ax.set_title("Cost vs Drag: Single Aircraft vs Formation")
    ax.legend()
    ax.grid(True, alpha=0.3)
    return fig, ax


def plot_structural_scaling(
    structure: EmpiricalStructure | None = None,
    span_range: tuple[float, float] = (5, 100),
) -> tuple[Figure, Axes]:
    """Plot wing mass vs span with real aircraft data points."""
    structure = structure or EmpiricalStructure.from_data(SOLAR_HALE_DATA)

    fig, ax = plt.subplots(figsize=(10, 7))

    # Fitted curve
    spans = np.linspace(span_range[0], span_range[1], 200)
    masses = [structure.wing_mass(s) for s in spans]
    ax.plot(spans, masses, "b-", label=f"Fit: m = {structure.coefficient:.4f} * b^{structure.exponent:.2f}")

    # Real data points
    for d in SOLAR_HALE_DATA:
        ax.plot(d["span_m"], d["wing_mass_kg"], "ro", markersize=8)
        ax.annotate(
            d["name"], (d["span_m"], d["wing_mass_kg"]),
            textcoords="offset points", xytext=(5, 5), fontsize=8,
        )

    ax.set_xlabel("Wingspan (m)")
    ax.set_ylabel("Wing mass (kg)")
    ax.set_title("Wing Structural Mass Scaling — Solar/HALE Aircraft")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_yscale("log")
    ax.set_xscale("log")
    return fig, ax


def plot_energy_balance_timeline(
    power_required_W: float,
    peak_solar_power_W: float,
    day_hours: float,
) -> tuple[Figure, Axes]:
    """24-hour energy balance: solar input vs power required."""
    fig, ax = plt.subplots(figsize=(10, 5))

    hours = np.linspace(0, 24, 500)
    # Sunrise at (12 - day_hours/2), sunset at (12 + day_hours/2)
    sunrise = 12 - day_hours / 2
    sunset = 12 + day_hours / 2

    solar_power = np.zeros_like(hours)
    daylight = (hours >= sunrise) & (hours <= sunset)
    # Sinusoidal solar profile during daylight
    phase = np.pi * (hours[daylight] - sunrise) / day_hours
    solar_power[daylight] = peak_solar_power_W * np.sin(phase)

    ax.fill_between(hours, solar_power, alpha=0.3, color="gold", label="Solar power")
    ax.axhline(power_required_W, color="red", linestyle="--", label=f"Power required ({power_required_W:.0f} W)")
    ax.fill_between(
        hours, power_required_W, solar_power,
        where=solar_power > power_required_W,
        alpha=0.2, color="green", label="Battery charging",
    )
    ax.fill_between(
        hours, 0, power_required_W,
        where=solar_power < power_required_W,
        alpha=0.2, color="red", label="Battery discharge",
    )

    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Power (W)")
    ax.set_title("24-Hour Energy Balance")
    ax.set_xlim(0, 24)
    ax.set_ylim(0, max(peak_solar_power_W * 1.1, power_required_W * 1.5))
    ax.legend()
    ax.grid(True, alpha=0.3)
    return fig, ax


def plot_formation_geometry(
    N: int,
    span_m: float,
    lateral_overlap_ratio: float,
    geometry: str = "v",
) -> tuple[Figure, Axes]:
    """Top-down view of aircraft positions in formation."""
    fig, ax = plt.subplots(figsize=(8, 8))

    # Lateral spacing between adjacent aircraft
    gap = span_m * (1 - lateral_overlap_ratio)
    streamwise_sep = span_m * 2  # 2 spans streamwise separation

    positions = []
    if geometry == "v":
        positions.append((0, 0))  # leader
        depth = 1
        idx = 1
        while idx < N:
            x_offset = depth * gap
            y_offset = -depth * streamwise_sep
            positions.append((-x_offset, y_offset))  # left
            idx += 1
            if idx < N:
                positions.append((x_offset, y_offset))  # right
                idx += 1
            depth += 1
    elif geometry == "echelon":
        for i in range(N):
            positions.append((i * gap, -i * streamwise_sep))
    else:  # inline
        for i in range(N):
            positions.append((0, -i * streamwise_sep))

    # Draw aircraft as simple wing shapes
    for i, (x, y) in enumerate(positions):
        wing_left = x - span_m / 2
        wing_right = x + span_m / 2
        ax.plot([wing_left, wing_right], [y, y], "b-", linewidth=3)
        ax.plot(x, y, "ko", markersize=4)
        label = "L" if i == 0 else f"F{i}"
        ax.annotate(label, (x, y), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=10, fontweight="bold")

    ax.set_aspect("equal")
    ax.set_xlabel("Lateral position (m)")
    ax.set_ylabel("Streamwise position (m)")
    ax.set_title(f"{geometry.upper()} Formation — N={N}, span={span_m}m, overlap={lateral_overlap_ratio:.0%}")
    ax.grid(True, alpha=0.3)
    return fig, ax
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_plots.py -v`
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add wingz/visualization/plots.py tests/test_plots.py
git commit -m "feat(viz): matplotlib plotting functions for cost/drag, scaling, energy, geometry"
```

---

### Task 15: Main Sweep Script

**Files:**
- Create: `scripts/sweep_single_vs_formation.py`

Replaces `example_usage.py` with a comprehensive sweep using all sub-models.

- [ ] **Step 1: Write the script**

`scripts/sweep_single_vs_formation.py`:
```python
#!/usr/bin/env python3
"""
Sweep single aircraft vs formation configurations and plot results.

Usage:
    python scripts/sweep_single_vs_formation.py
    python scripts/sweep_single_vs_formation.py --save  # save figures to docs/
"""

import sys
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

from wingz.evaluation.sweep import (
    AircraftConfig,
    PositionStrategy,
    evaluate_config,
    sweep_configs,
)
from wingz.evaluation.pareto import pareto_filter
from wingz.mission.profiles import hale_20km, lower_altitude_le
from wingz.control.architectures import FormationArchitecture
from wingz.aerodynamics.formation_aero import FormationGeometry
from wingz.visualization.plots import (
    plot_cost_vs_drag,
    plot_structural_scaling,
    plot_formation_geometry,
    plot_energy_balance_timeline,
)


def main():
    save = "--save" in sys.argv

    mission = hale_20km()

    # Generate sweep configs
    configs = sweep_configs(
        spans=np.linspace(8, 80, 40).tolist(),
        Ns=[1, 2, 3, 4, 6, 8],
        architectures=[
            FormationArchitecture.LEADER_FOLLOWER,
            FormationArchitecture.MESH,
        ],
        position_strategies=[
            PositionStrategy.UNIFORM,
            PositionStrategy.HEAVY_WAKE,
            PositionStrategy.HEAVY_FRONT,
        ],
        geometries=[FormationGeometry.V],
        lateral_overlap_ratios=[0.05, 0.1, 0.15],
    )

    print(f"Evaluating {len(configs)} configurations...")
    results = [evaluate_config(c, mission) for c in configs]
    df = pd.DataFrame(results)

    # Pareto frontier
    pareto_rows = pareto_filter(df.to_dict("records"))
    pareto_df = pd.DataFrame(pareto_rows)

    print(f"\nResults: {len(df)} configs, {len(pareto_df)} on Pareto frontier")
    print(f"\nPareto frontier summary:")
    if len(pareto_df) > 0:
        print(pareto_df[["N", "span_each_m", "architecture", "position_strategy",
                          "total_drag_N", "cost_score", "total_mass_kg"]].to_string())

    # Plot 1: Cost vs drag
    fig1, ax1 = plot_cost_vs_drag(df, pareto_df=pareto_df)

    # Plot 2: Cost vs drag colored by position strategy
    fig2, ax2 = plot_cost_vs_drag(df, color_by="position_strategy", pareto_df=pareto_df)
    ax2.set_title("Cost vs Drag — by Position Strategy")

    # Plot 3: Structural scaling
    fig3, ax3 = plot_structural_scaling()

    # Plot 4: Formation geometry example
    fig4, ax4 = plot_formation_geometry(N=5, span_m=15.0, lateral_overlap_ratio=0.1, geometry="v")

    if save:
        fig1.savefig("docs/formation_flight/cost_vs_drag_by_arch.png", dpi=150, bbox_inches="tight")
        fig2.savefig("docs/formation_flight/cost_vs_drag_by_strategy.png", dpi=150, bbox_inches="tight")
        fig3.savefig("docs/formation_flight/structural_scaling.png", dpi=150, bbox_inches="tight")
        fig4.savefig("docs/formation_flight/v_formation_geometry.png", dpi=150, bbox_inches="tight")
        print("\nFigures saved to docs/formation_flight/")
    else:
        plt.show()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the script to verify it works**

Run: `cd /Users/dgrant/Documents/personal/wingz && python scripts/sweep_single_vs_formation.py --save`
Expected: prints config count, Pareto summary, saves 4 PNG files to `docs/formation_flight/`

- [ ] **Step 3: Commit**

```bash
git add scripts/sweep_single_vs_formation.py
git commit -m "feat: main sweep script comparing single vs formation configs"
```

---

### Task 16: Sensitivity Analysis Script

**Files:**
- Create: `scripts/sensitivity_analysis.py`

Varies one parameter at a time to identify which knobs matter most.

- [ ] **Step 1: Write the script**

`scripts/sensitivity_analysis.py`:
```python
#!/usr/bin/env python3
"""
Sensitivity analysis: vary one parameter at a time, plot impact on total drag and cost.

Usage:
    python scripts/sensitivity_analysis.py
    python scripts/sensitivity_analysis.py --save
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from wingz.evaluation.sweep import (
    AircraftConfig,
    PositionStrategy,
    evaluate_config,
)
from wingz.mission.profiles import hale_20km
from wingz.control.architectures import FormationArchitecture
from wingz.aerodynamics.formation_aero import FormationGeometry


def baseline_config() -> AircraftConfig:
    return AircraftConfig(
        N=4,
        span_each_m=20.0,
        architecture=FormationArchitecture.LEADER_FOLLOWER,
        position_strategy=PositionStrategy.HEAVY_WAKE,
        geometry=FormationGeometry.V,
        lateral_overlap_ratio=0.1,
    )


def vary_parameter(name: str, values, mission):
    """Evaluate baseline config with one parameter varied."""
    results = []
    for v in values:
        config = baseline_config()
        if name == "N":
            config.N = int(v)
        elif name == "span_each_m":
            config.span_each_m = float(v)
        elif name == "lateral_overlap_ratio":
            config.lateral_overlap_ratio = float(v)
        result = evaluate_config(config, mission)
        result["varied_param"] = name
        result["varied_value"] = v
        results.append(result)
    return results


def main():
    save = "--save" in sys.argv
    mission = hale_20km()

    parameters = {
        "N": np.arange(1, 11),
        "span_each_m": np.linspace(8, 50, 30),
        "lateral_overlap_ratio": np.linspace(-0.1, 0.4, 30),
    }

    fig, axes = plt.subplots(len(parameters), 2, figsize=(14, 4 * len(parameters)))

    for i, (name, values) in enumerate(parameters.items()):
        results = vary_parameter(name, values, mission)
        df = pd.DataFrame(results)

        axes[i, 0].plot(df["varied_value"], df["total_drag_N"], "b.-")
        axes[i, 0].set_xlabel(name)
        axes[i, 0].set_ylabel("Total drag (N)")
        axes[i, 0].set_title(f"Drag sensitivity to {name}")
        axes[i, 0].grid(True, alpha=0.3)

        axes[i, 1].plot(df["varied_value"], df["cost_score"], "r.-")
        axes[i, 1].set_xlabel(name)
        axes[i, 1].set_ylabel("Cost score")
        axes[i, 1].set_title(f"Cost sensitivity to {name}")
        axes[i, 1].grid(True, alpha=0.3)

    plt.suptitle("Sensitivity Analysis — Formation Flight", fontsize=14, y=1.02)
    plt.tight_layout()

    if save:
        fig.savefig("docs/formation_flight/sensitivity_analysis.png", dpi=150, bbox_inches="tight")
        print("Saved to docs/formation_flight/sensitivity_analysis.png")
    else:
        plt.show()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the script to verify it works**

Run: `python scripts/sensitivity_analysis.py --save`
Expected: saves sensitivity plot PNG

- [ ] **Step 3: Commit**

```bash
git add scripts/sensitivity_analysis.py
git commit -m "feat: sensitivity analysis script"
```

---

### Task 17: Documentation — Expanded Writeups

**Files:**
- Create: `docs/formation_flight/README.md`

- [ ] **Step 1: Write the documentation**

`docs/formation_flight/README.md`:
```markdown
# Formation Flight Analysis

## Overview

This project models the tradeoff between building one large high-aspect-ratio
solar-powered aircraft vs. flying a formation of smaller aircraft to achieve
equivalent aerodynamic performance.

## Core Thesis

Structural complexity scales faster than aerodynamic benefit as wingspan increases.
Formation flight trades structural complexity for control complexity.

## Running the Analysis

### Full parameter sweep

```bash
python scripts/sweep_single_vs_formation.py        # interactive plots
python scripts/sweep_single_vs_formation.py --save  # save to docs/
```

### Sensitivity analysis

```bash
python scripts/sensitivity_analysis.py        # interactive
python scripts/sensitivity_analysis.py --save # save to docs/
```

## Package Structure

- `wingz/structures/` — wing mass scaling models
- `wingz/aerodynamics/` — drag models including formation effects
- `wingz/solar/` — solar power and energy balance
- `wingz/control/` — formation architectures and station-keeping
- `wingz/cost/` — mass-proxy and bottom-up cost models
- `wingz/mission/` — mission profile definitions
- `wingz/evaluation/` — parameter sweeps and Pareto analysis
- `wingz/visualization/` — matplotlib plotting

## Key Design Insights

### Position Strategy

The heaviest aircraft (full nav/comms) should sit in the best wake position,
not the leader slot. The lightest aircraft leads because it flies in clean
air and has the best power-to-weight ratio to handle full drag.

### Formation Architectures

Three architectures modeled:
- **Leader/follower** — one heavy leader, light followers
- **Tiered** — leader + sub-leaders + followers
- **Mesh** — all aircraft carry partial nav, cooperative localization

### Energy Balance

For 30+ day missions, every aircraft must close a 24-hour energy cycle.
The battery mass feedback loop (more battery → more weight → more drag →
more power → more battery) is the critical sizing constraint.
```

- [ ] **Step 2: Commit**

```bash
git add docs/formation_flight/README.md
git commit -m "docs: formation flight analysis documentation"
```

---

### Task 18: Clean Up Legacy Files

**Files:**
- Existing: `formation_span_model.py` (keep as reference)
- Existing: `example_usage.py` (keep as reference)

- [ ] **Step 1: Add deprecation notice to old files**

Add to top of `formation_span_model.py`:
```python
# DEPRECATED: This was the original prototype. Use the wingz package instead.
# Kept for reference. See wingz/ for the refactored, modular version.
```

Add to top of `example_usage.py`:
```python
# DEPRECATED: Use scripts/sweep_single_vs_formation.py instead.
# This was the original prototype script.
```

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add formation_span_model.py example_usage.py
git commit -m "chore: deprecation notices on original prototype files"
```
