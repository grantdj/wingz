
# DEPRECATED: Use scripts/sweep_single_vs_formation.py instead.
# This was the original prototype script.

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from formation_span_model import (
    Mission, StructureModel, FormationModel,
    sweep_single, sweep_formation, pareto_filter
)

mission = Mission(
    total_weight_N=1000,
    rho=0.0889,
    velocity=25,
    wing_loading_N_m2=45,
    oswald_e=0.85,
    cd0=0.025,
)

structure = StructureModel(
    reference_span_m=20,
    reference_wing_mass_kg=20,
    span_exponent=2.3,
    material_cost_per_kg=150,
    manufacturing_exponent=1.2,
)

formation = FormationModel(
    formation_induced_drag_factor=0.75,
    control_cost_per_aircraft=1000,
    coordination_cost_exponent=1.2,
)

single_rows = sweep_single(np.linspace(10, 80, 80), mission, structure)
formation_rows = sweep_formation(np.linspace(8, 30, 60), [2, 3, 4, 6, 8], mission, structure, formation)

df = pd.DataFrame(single_rows + formation_rows)
pareto = pd.DataFrame(pareto_filter(df.to_dict("records")))

plt.figure()
for config, group in df.groupby("configuration"):
    plt.scatter(group["total_cost"], group["total_drag_N"], label=config, alpha=0.6)
plt.scatter(pareto["total_cost"], pareto["total_drag_N"], marker="x", label="Pareto frontier")
plt.xlabel("Total model cost")
plt.ylabel("Total drag, N")
plt.title("Cost vs drag: single wing vs formation")
plt.legend()
plt.show()
