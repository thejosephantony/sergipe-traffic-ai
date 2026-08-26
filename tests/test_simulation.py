from sergipe_traffic_ai.controllers import FixedController
from sergipe_traffic_ai.simulation import Simulation


def test_simulation_is_reproducible():
    first = Simulation(FixedController(), seed=123).run(100)
    second = Simulation(FixedController(), seed=123).run(100)
    assert first == second


def test_simulation_generates_metrics():
    summary = Simulation(FixedController(), seed=42).run(50)
    assert summary["vehicles_generated"] >= summary["vehicles_completed"]
    assert summary["max_queue"] >= 0
