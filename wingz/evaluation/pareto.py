"""
Multi-objective Pareto analysis.
Filters configurations to those not dominated in the objective space.
Lower is better for all objectives.
"""

import numpy as np


def pareto_filter(rows: list[dict], x_key: str = "cost_score", y_key: str = "total_drag_N") -> list[dict]:
    if not rows:
        return []
    sorted_rows = sorted(rows, key=lambda r: (r[x_key], r[y_key]))
    pareto = []
    best_y = np.inf
    for row in sorted_rows:
        if row[y_key] < best_y:
            pareto.append(row)
            best_y = row[y_key]
    return pareto
