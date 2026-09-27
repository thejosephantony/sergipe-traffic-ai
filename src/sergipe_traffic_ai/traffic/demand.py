from __future__ import annotations

import random
from typing import Any, Dict, List


BARAO_AXIS = "Av. Barão de Maruim / Des. Maynard"
AUGUSTO_AXIS = "Av. Augusto Franco"


class Vehicle:
    """Veículo simples usado pelo protótipo de dinâmica causal."""

    def __init__(self, vehicle_id: int, origin_axis: str, destination: str):
        self.vehicle_id = vehicle_id
        self.origin_axis = origin_axis
        self.destination = destination
        self.position = -120.0
        self.speed = 10.0
        self.state = "MOVING"
        self.wait_time_s = 0.0


class TrafficDemandSimulator:
    """
    Gerador de demanda + dinâmica veicular simplificada.

    A posição é longitudinal em metros:
    -120 m = entrada da aproximação
       0 m = linha de parada
      80 m = saída do cruzamento
    """

    def __init__(self, scenario_config: Dict[str, Any]):
        self.config = scenario_config["scenario"]
        self.seed = self.config.get("seed", 42)
        self.duration_s = self.config.get("duration_s", 1800)
        self.time_step_s = self.config.get("time_step_s", 0.2)

        demands = self.config.get("demand", {})
        self.rate_barao_maynard = demands.get("axis_barao_maynard_rate", 0.80)
        self.rate_augusto_franco = demands.get("axis_augusto_franco_rate", 0.75)

        self.spawn_position_m = -120.0
        self.stop_line_position_m = 0.0
        self.exit_position_m = 80.0
        self.vehicle_length_m = 4.5
        self.min_gap_m = 2.5
        self.desired_speed_m_s = 10.0

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

    def _axis_vehicles(self, axis_name: str) -> List[Vehicle]:
        return [v for v in self.active_vehicles if v.origin_axis == axis_name]

    def _can_spawn(self, axis_name: str) -> bool:
        vehicles = self._axis_vehicles(axis_name)
        if not vehicles:
            return True
        rear_vehicle = min(vehicles, key=lambda v: v.position)
        minimum_spacing = self.vehicle_length_m + self.min_gap_m
        return rear_vehicle.position > self.spawn_position_m + minimum_spacing

    def _spawn_vehicle(self, axis_name: str, destination: str) -> Vehicle | None:
        if not self._can_spawn(axis_name):
            return None

        self.vehicle_counter += 1
        vehicle = Vehicle(self.vehicle_counter, axis_name, destination)
        self.active_vehicles.append(vehicle)
        return vehicle

    def generate_vehicles_step(self) -> List[Vehicle]:
        """Gera novas chegadas uma única vez para o passo atual."""
        new_vehicles: List[Vehicle] = []

        if self.rng.random() < (self.rate_barao_maynard * self.time_step_s):
            vehicle = self._spawn_vehicle(BARAO_AXIS, "Centro/Oeste")
            if vehicle is not None:
                new_vehicles.append(vehicle)

        if self.rng.random() < (self.rate_augusto_franco * self.time_step_s):
            vehicle = self._spawn_vehicle(AUGUSTO_AXIS, "Sul/Norte")
            if vehicle is not None:
                new_vehicles.append(vehicle)

        return new_vehicles

    @staticmethod
    def _axis_has_green(axis_name: str, phase: str | None) -> bool:
        if phase is None:
            return False
        if axis_name == BARAO_AXIS:
            return phase == "BARAO_GREEN"
        return phase == "AUGUSTO_GREEN"

    def _update_axis(self, axis_name: str, phase: str | None):
        vehicles = sorted(
            self._axis_vehicles(axis_name),
            key=lambda vehicle: vehicle.position,
            reverse=True,
        )
        if not vehicles:
            return

        green = self._axis_has_green(axis_name, phase)
        spacing = self.vehicle_length_m + self.min_gap_m
        leader_position: float | None = None

        for vehicle in vehicles:
            if leader_position is None:
                limit = self.exit_position_m if green else self.stop_line_position_m
            else:
                limit = leader_position - spacing

            requested_position = vehicle.position + self.desired_speed_m_s * self.time_step_s
            new_position = min(requested_position, limit)

            moved = new_position > vehicle.position + 1e-9
            vehicle.position = new_position

            if moved:
                vehicle.speed = self.desired_speed_m_s
                vehicle.state = "MOVING"
            else:
                vehicle.speed = 0.0
                vehicle.state = "QUEUED"
                vehicle.wait_time_s = round(vehicle.wait_time_s + self.time_step_s, 2)

            leader_position = vehicle.position

    def step(self, current_phase: str | None = None):
        """
        Avança a dinâmica sem gerar demanda novamente.

        A chamada correta por passo é:
        generate_vehicles_step() -> controlador.decide(...) -> step(fase)
        """
        if self.current_time >= self.duration_s:
            return False

        self._update_axis(BARAO_AXIS, current_phase)
        self._update_axis(AUGUSTO_AXIS, current_phase)

        remaining: List[Vehicle] = []
        for vehicle in self.active_vehicles:
            if vehicle.position >= self.exit_position_m - 1e-9:
                vehicle.state = "COMPLETED"
                self.completed_vehicles_count += 1
            else:
                remaining.append(vehicle)
        self.active_vehicles = remaining

        self.current_time = round(self.current_time + self.time_step_s, 2)
        return self.current_time < self.duration_s

    def queue_length(self, axis_name: str) -> int:
        return sum(
            1
            for vehicle in self.active_vehicles
            if vehicle.origin_axis == axis_name and vehicle.state == "QUEUED"
        )

    def average_wait(self, axis_name: str | None = None) -> float:
        vehicles = self.active_vehicles
        if axis_name is not None:
            vehicles = [v for v in vehicles if v.origin_axis == axis_name]
        if not vehicles:
            return 0.0
        return sum(v.wait_time_s for v in vehicles) / len(vehicles)
