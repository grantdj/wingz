from wingz.evaluation.pareto import pareto_filter


def test_pareto_filters_dominated():
    rows = [
        {"cost": 10, "drag": 10},
        {"cost": 5, "drag": 5},
        {"cost": 3, "drag": 8},
        {"cost": 8, "drag": 3},
    ]
    result = pareto_filter(rows, x_key="cost", y_key="drag")
    assert len(result) == 3
    assert {"cost": 10, "drag": 10} not in result


def test_pareto_single_row():
    rows = [{"cost": 5, "drag": 5}]
    result = pareto_filter(rows, x_key="cost", y_key="drag")
    assert len(result) == 1


def test_pareto_empty():
    result = pareto_filter([], x_key="cost", y_key="drag")
    assert len(result) == 0
