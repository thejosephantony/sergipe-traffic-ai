from __future__ import annotations

import random
from typing import Any, Dict, List


BARAO_AXIS = "Av. Barão de Maruim / Des. Maynard"
AUGUSTO_AXIS = "Av. Augusto Franco"

VEHICLE_PROFILES = {
    "car": {
        "length_m": 4.5,
        "desired_speed_m_s": 10.0,
    },
    "motorcycle": {
        "length_m": 2.2,
        "desired_speed_m_s": 11.5,
    },
    "bus": {
        "length_m": 10.5,
        "desired_speed_m_s": 8.0,
    },
}

DEFAULT_VEHICLE_MIX = {
    "car": 0.72,
    "motorcycle": 0.18,
    "bus": 0.10,
}


class Vehicle:
    """Agente veicular simples usado pelo protótipo de dinâmica causal."""

    def __init__(
        self,
        vehicle_id: int,
        origin_axis: str,
        destination: str,
        vehicle_type: str = "car",
    ):
        if vehicle_type not in VEHICLE_PROFILES:
            raise ValueError(f"Tipo de veículo desconhecido: {vehicle_type}")

        profile = VEHICLE_PROFILES[vehicle_type]

        self.vehicle_id = vehicle_id
        self.origin_axis = origin_axis
        self.destination = destination
        self.vehicle_type = vehicle_type

        self.length_m = float(profile["length_m"])
        self.desired_speed_m_s = float(profile["desired_speed_m_s"])

        self.position = -120.0
        self.speed = self.desired_speed_m_s
        self.state = "MOVING"
        self.wait_time_s = 0.0


class TrafficDemandSimulator:
    """
    Gerador de demanda + dinâmica veicular simplificada.

    A posição é longitudinal em metros:
    -120 m = entrada da aproximação
       0 m = linha de parada
      80 m = saída do cruzamento

    A composição da frota é configurável e, por padrão, sintética.
    """

    def __init__(self, scenario_config: Dict[str, Any]):
        self.config = scenario_config["scenario"]
        self.seed = self.config.get("seed", 42)
        self.duration_s = self.config.get("duration_s", 1800)
        self.time_step_s = self.config.get("time_step_s", 0.2)

        demands = self.config.get("demand", {})
        self.rate_barao_maynard = demands.get("axis_barao_maynard_rate", 0.80)
        self.rate_augusto_franco = demands.get("axis_augusto_franco_rate", 0.75)
        self.vehicle_mix = self._normalize_vehicle_mix(
            demands.get("vehicle_mix", DEFAULT_VEHICLE_MIX)
        )

        self.spawn_position_m = -120.0
        self.stop_line_position_m = 0.0
        self.exit_position_m = 80.0
        self.min_gap_m = 2.5

        self.rng = random.Random(self.seed)
        self.current_time = 0.0
        self.vehicle_counter = 0
        self.active_vehicles: List[Vehicle] = []
        self.completed_vehicles_count = 0
        self.completed_vehicles_by_type = {
            vehicle_type: 0 for vehicle_type in VEHICLE_PROFILES
        }

    @staticmethod
    def _normalize_vehicle_mix(raw_mix: Dict[str, Any]) -> Dict[str, float]:
        filtered = {
            vehicle_type: max(0.0, float(raw_mix.get(vehicle_type, 0.0)))
            for vehicle_type in VEHICLE_PROFILES
        }
        total = sum(filtered.values())

        if total <= 0:
            return DEFAULT_VEHICLE_MIX.copy()

        return {
            vehicle_type: weight / total
            for vehicle_type, weight in filtered.items()
        }

    def reset(self):
        self.rng = random.Random(self.seed)
        self.current_time = 0.0
        self.vehicle_counter = 0
        self.active_vehicles.clear()
        self.completed_vehicles_count = 0
        self.completed_vehicles_by_type = {
            vehicle_type: 0 for vehicle_type in VEHICLE_PROFILES
        }

    def _axis_vehicles(self, axis_name: str) -> List[Vehicle]:
        return [v for v in self.active_vehicles if v.origin_axis == axis_name]

    def _can_spawn(self, axis_name: str) -> bool:
        vehicles = self._axis_vehicles(axis_name)
        if not vehicles:
            return True

        rear_vehicle = min(vehicles, key=lambda v: v.position)
        minimum_spacing = rear_vehicle.length_m + self.min_gap_m
        return rear_vehicle.position > self.spawn_position_m + minimum_spacing

    def _sample_vehicle_type(self) -> str:
        threshold = self.rng.random()
        cumulative = 0.0

        for vehicle_type, weight in self.vehicle_mix.items():
            cumulative += weight
            if threshold <= cumulative:
                return vehicle_type

        return "car"

    def _spawn_vehicle(
        self,
        axis_name: str,
        destination: str,
        vehicle_type: str | None = None,
    ) -> Vehicle | None:
        if not self._can_spawn(axis_name):
            return None

        selected_type = vehicle_type or self._sample_vehicle_type()
        self.vehicle_counter += 1
        vehicle = Vehicle(
            self.vehicle_counter,
            axis_name,
            destination,
            selected_type,
        )
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
        leader: Vehicle | None = None

        for vehicle in vehicles:
            if leader is None:
                limit = (
                    self.exit_position_m
                    if green
                    else self.stop_line_position_m
                )
            else:
                limit = leader.position - leader.length_m - self.min_gap_m

            requested_position = (
                vehicle.position
                + vehicle.desired_speed_m_s * self.time_step_s
            )
            new_position = min(requested_position, limit)

            moved = new_position > vehicle.position + 1e-9
            vehicle.position = new_position

            if moved:
                vehicle.speed = vehicle.desired_speed_m_s
                vehicle.state = "MOVING"
            else:
                vehicle.speed = 0.0
                vehicle.state = "QUEUED"
                vehicle.wait_time_s = round(
                    vehicle.wait_time_s + self.time_step_s,
                    2,
                )

            leader = vehicle

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
                self.completed_vehicles_by_type[vehicle.vehicle_type] += 1
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
            vehicles = [
                v for v in vehicles if v.origin_axis == axis_name
            ]
        if not vehicles:
            return 0.0
        return sum(v.wait_time_s for v in vehicles) / len(vehicles)

    def active_count_by_type(self, vehicle_type: str) -> int:
        return sum(
            1
            for vehicle in self.active_vehicles
            if vehicle.vehicle_type == vehicle_type
        )
