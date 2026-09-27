from sergipe_traffic_ai.traffic.demand import (
    AUGUSTO_AXIS,
    BARAO_AXIS,
    TrafficDemandSimulator,
)


def scenario(seed=42):
    return {
        "scenario": {
            "seed": seed,
            "duration_s": 20.0,
            "time_step_s": 0.2,
            "demand": {
                "axis_barao_maynard_rate": 0.8,
                "axis_augusto_franco_rate": 0.75,
            },
        }
    }


def test_demand_is_reproducible():
    first = TrafficDemandSimulator(scenario(123))
    second = TrafficDemandSimulator(scenario(123))

    seq1 = []
    seq2 = []

    for _ in range(50):
        seq1.append(
            [
                (v.vehicle_id, v.origin_axis, v.vehicle_type)
                for v in first.generate_vehicles_step()
            ]
        )
        first.step("BARAO_GREEN")

        seq2.append(
            [
                (v.vehicle_id, v.origin_axis, v.vehicle_type)
                for v in second.generate_vehicles_step()
            ]
        )
        second.step("BARAO_GREEN")

    assert seq1 == seq2


def test_red_axis_accumulates_queue_and_wait():
    sim = TrafficDemandSimulator(scenario())
    sim.rate_barao_maynard = 0.0
    sim.rate_augusto_franco = 0.0

    vehicle = sim._spawn_vehicle(AUGUSTO_AXIS, "Sul/Norte")
    assert vehicle is not None

    for _ in range(80):
        sim.step("BARAO_GREEN")

    assert sim.queue_length(AUGUSTO_AXIS) >= 1
    assert sim.average_wait(AUGUSTO_AXIS) > 0


def test_green_axis_completes_vehicle():
    sim = TrafficDemandSimulator(scenario())
    sim.rate_barao_maynard = 0.0
    sim.rate_augusto_franco = 0.0

    vehicle = sim._spawn_vehicle(BARAO_AXIS, "Centro/Oeste")
    assert vehicle is not None

    for _ in range(120):
        sim.step("BARAO_GREEN")
        if sim.completed_vehicles_count:
            break

    assert sim.completed_vehicles_count == 1
    assert vehicle not in sim.active_vehicles


def test_vehicle_types_have_distinct_profiles():
    sim = TrafficDemandSimulator(scenario())
    sim.rate_barao_maynard = 0.0
    sim.rate_augusto_franco = 0.0

    car = sim._spawn_vehicle(BARAO_AXIS, "Centro/Oeste", "car")
    assert car is not None

    sim.active_vehicles.clear()
    motorcycle = sim._spawn_vehicle(
        BARAO_AXIS,
        "Centro/Oeste",
        "motorcycle",
    )
    assert motorcycle is not None

    sim.active_vehicles.clear()
    bus = sim._spawn_vehicle(BARAO_AXIS, "Centro/Oeste", "bus")
    assert bus is not None

    assert motorcycle.length_m < car.length_m < bus.length_m
    assert motorcycle.desired_speed_m_s > car.desired_speed_m_s > bus.desired_speed_m_s


def test_vehicle_mix_is_normalized():
    config = scenario()
    config["scenario"]["demand"]["vehicle_mix"] = {
        "car": 72,
        "motorcycle": 18,
        "bus": 10,
    }

    sim = TrafficDemandSimulator(config)

    assert round(sum(sim.vehicle_mix.values()), 10) == 1.0
    assert sim.vehicle_mix["car"] == 0.72
    assert sim.vehicle_mix["motorcycle"] == 0.18
    assert sim.vehicle_mix["bus"] == 0.10


def test_completed_vehicles_are_counted_by_type():
    sim = TrafficDemandSimulator(scenario())
    sim.rate_barao_maynard = 0.0
    sim.rate_augusto_franco = 0.0

    bus = sim._spawn_vehicle(BARAO_AXIS, "Centro/Oeste", "bus")
    assert bus is not None

    for _ in range(200):
        sim.step("BARAO_GREEN")
        if sim.completed_vehicles_count:
            break

    assert sim.completed_vehicles_count == 1
    assert sim.completed_vehicles_by_type["bus"] == 1
