import random
from typing import Dict, Any, List

class Vehicle:
    def __init__(self, vehicle_id: int, origin_axis: str, destination: str):
        self.vehicle_id = vehicle_id
        self.origin_axis = origin_axis
        self.destination = destination
        self.position = 0.0
        self.speed = 10.0
        self.state = "MOVING"
        self.wait_time_s = 0.0

class TrafficDemandSimulator:
    def __init__(self, scenario_config: Dict[str, Any]):
        self.config = scenario_config["scenario"]
        self.seed = self.config.get("seed", 42)
        self.duration_s = self.config.get("duration_s", 1800)
        self.time_step_s = self.config.get("time_step_s", 0.2)
        
        demands = self.config.get("demand", {})
        self.rate_barao_maynard = demands.get("axis_barao_maynard_rate", 0.80)
        self.rate_augusto_franco = demands.get("axis_augusto_franco_rate", 0.75)
        
        self.rng = random.Random(self.seed)
        self.current_time = 0.0
        self.vehicle_counter = 0
        self.active_vehicles: List[Vehicle] = []
        self.completed_vehicles_count = 0

    def reset(self):
        self.rng = random.Random(self.seed)
        self.current_time = 0.0
        self.vehicle_counter = 0
        self.active_vehicles.clear()
        self.completed_vehicles_count = 0

    def generate_vehicles_step(self) -> List[Vehicle]:
        new_vehicles = []
        if self.rng.random() < (self.rate_barao_maynard * self.time_step_s):
            self.vehicle_counter += 1
            v = Vehicle(self.vehicle_counter, "Av. Barão de Maruim / Des. Maynard", "Centro/Oeste")
            new_vehicles.append(v)
            self.active_vehicles.append(v)

        if self.rng.random() < (self.rate_augusto_franco * self.time_step_s):
            self.vehicle_counter += 1
            v = Vehicle(self.vehicle_counter, "Av. Augusto Franco", "Sul/Norte")
            new_vehicles.append(v)
            self.active_vehicles.append(v)

        return new_vehicles

    def step(self):
        if self.current_time >= self.duration_s:
            return False
        self.generate_vehicles_step()
        self.current_time = round(self.current_time + self.time_step_s, 2)
        return True
