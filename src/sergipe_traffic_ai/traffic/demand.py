from __future__ import annotations

import random
from typing import Any, Dict, List


BARAO_AXIS = "Av. Barão de Maruim / Des. Maynard"
AUGUSTO_AXIS = "Av. Augusto Franco"

BARAO_EASTBOUND = "barao_eastbound"
BARAO_WESTBOUND = "barao_westbound"
AUGUSTO_NORTHBOUND = "augusto_northbound"
AUGUSTO_SOUTHBOUND = "augusto_southbound"

MOVEMENTS_BY_AXIS = {
    BARAO_AXIS: (BARAO_EASTBOUND, BARAO_WESTBOUND),
    AUGUSTO_AXIS: (AUGUSTO_NORTHBOUND, AUGUSTO_SOUTHBOUND),
}

DEFAULT_DIRECTION_SPLIT = {
    BARAO_EASTBOUND: 0.50,
    BARAO_WESTBOUND: 0.50,
    AUGUSTO_NORTHBOUND: 0.50,
    AUGUSTO_SOUTHBOUND: 0.50,
}

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
        movement: str | None = None,
    ):
        if vehicle_type not in VEHICLE_PROFILES:
            raise ValueError(f"Tipo de veículo desconhecido: {vehicle_type}")

        valid_movements = MOVEMENTS_BY_AXIS[origin_axis]
        selected_movement = movement or valid_movements[0]
        if selected_movement not in valid_movements:
            raise ValueError(
                f"Movimento {selected_movement} incompatível com {origin_axis}"
            )

        profile = VEHICLE_PROFILES[vehicle_type]

        self.vehicle_id = vehicle_id
        self.origin_axis = origin_axis
        self.destination = destination
        self.vehicle_type = vehicle_type
        self.movement = selected_movement

        self.length_m = float(profile["length_m"])
        self.desired_speed_m_s = float(profile["desired_speed_m_s"])

        # Coordenada longitudinal relativa à linha de retenção.
        # 0 m = linha de retenção antes da faixa de pedestres.
        self.position = -95.0
        self.speed = self.desired_speed_m_s
        self.state = "MOVING"
        self.wait_time_s = 0.0


class TrafficDemandSimulator:
    """
    Gerador de demanda + dinâmica veicular simplificada.

    Cada sentido possui sua própria aproximação/fila.

    A posição longitudinal é relativa à linha de retenção:
      -95 m = entrada da aproximação
        0 m = linha de retenção antes da faixa de pedestres
      +95 m = saída do cruzamento

    A composição da frota e a divisão por sentido são sintéticas e
    configuráveis no cenário.
    """

    def __init__(self, scenario_config: Dict[str, Any]):
        self.config = scenario_config["scenario"]
        self.seed = self.config.get("seed", 42)
        self.duration_s = self.config.get("duration_s", 1800)
        self.time_step_s = self.config.get("time_step_s", 0.2)

        demands = self.config.get("demand", {})
        self.rate_barao_maynard = demands.get(
            "axis_barao_maynard_rate",
            0.80,
        )
        self.rate_augusto_franco = demands.get(
            "axis_augusto_franco_rate",
            0.75,
        )
        self.vehicle_mix = self._normalize_vehicle_mix(
            demands.get("vehicle_mix", DEFAULT_VEHICLE_MIX)
        )
        self.direction_split = self._normalize_direction_split(
            demands.get("direction_split", DEFAULT_DIRECTION_SPLIT)
        )

        self.spawn_position_m = -95.0
        self.stop_line_position_m = 0.0
        self.exit_position_m = 95.0
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

    @staticmethod
    def _normalize_direction_split(
        raw_split: Dict[str, Any],
    ) -> Dict[str, float]:
        normalized: Dict[str, float] = {}

        for movements in MOVEMENTS_BY_AXIS.values():
            first, second = movements
            first_weight = max(
                0.0,
                float(raw_split.get(first, DEFAULT_DIRECTION_SPLIT[first])),
            )
            second_weight = max(
                0.0,
                float(raw_split.get(second, DEFAULT_DIRECTION_SPLIT[second])),
            )
            total = first_weight + second_weight

            if total <= 0:
                normalized[first] = 0.5
                normalized[second] = 0.5
            else:
                normalized[first] = first_weight / total
                normalized[second] = second_weight / total

        return normalized

    def reset(self):
        self.rng = random.Random(self.seed)
        self.current_time = 0.0
        self.vehicle_counter = 0
        self.active_vehicles.clear()
        self.completed_vehicles_count = 0
        self.completed_vehicles_by_type = {
            vehicle_type: 0 for vehicle_type in VEHICLE_PROFILES
        }

    def _movement_vehicles(self, movement: str) -> List[Vehicle]:
        return [v for v in self.active_vehicles if v.movement == movement]

    def _can_spawn(self, movement: str) -> bool:
        vehicles = self._movement_vehicles(movement)
        if not vehicles:
            return True

        rear_vehicle = min(vehicles, key=lambda v: v.position)
        minimum_spacing = rear_vehicle.length_m + self.min_gap_m
        return (
            rear_vehicle.position
            > self.spawn_position_m + minimum_spacing
        )

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
        movement: str | None = None,
    ) -> Vehicle | None:
        valid_movements = MOVEMENTS_BY_AXIS[axis_name]
        selected_movement = movement or valid_movements[0]

        if selected_movement not in valid_movements:
            raise ValueError(
                f"Movimento {selected_movement} incompatível com {axis_name}"
            )

        if not self._can_spawn(selected_movement):
            return None

        selected_type = vehicle_type or self._sample_vehicle_type()
        self.vehicle_counter += 1
        vehicle = Vehicle(
            self.vehicle_counter,
            axis_name,
            destination,
            selected_type,
            selected_movement,
        )
        vehicle.position = self.spawn_position_m
        self.active_vehicles.append(vehicle)
        return vehicle

    def _generate_movement_arrival(
        self,
        axis_name: str,
        movement: str,
        axis_rate: float,
        destination: str,
    ) -> Vehicle | None:
        movement_rate = axis_rate * self.direction_split[movement]
        if self.rng.random() >= movement_rate * self.time_step_s:
            return None

        return self._spawn_vehicle(
            axis_name,
            destination,
            movement=movement,
        )

    def generate_vehicles_step(self) -> List[Vehicle]:
        """Gera chegadas independentes para os quatro sentidos."""
        new_vehicles: List[Vehicle] = []

        arrivals = (
            (
                BARAO_AXIS,
                BARAO_EASTBOUND,
                self.rate_barao_maynard,
                "Leste",
            ),
            (
                BARAO_AXIS,
                BARAO_WESTBOUND,
                self.rate_barao_maynard,
                "Oeste",
            ),
            (
                AUGUSTO_AXIS,
                AUGUSTO_NORTHBOUND,
                self.rate_augusto_franco,
                "Norte",
            ),
            (
                AUGUSTO_AXIS,
                AUGUSTO_SOUTHBOUND,
                self.rate_augusto_franco,
                "Sul",
            ),
        )

        for axis_name, movement, axis_rate, destination in arrivals:
            vehicle = self._generate_movement_arrival(
                axis_name,
                movement,
                axis_rate,
                destination,
            )
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

    def _update_movement(
        self,
        axis_name: str,
        movement: str,
        phase: str | None,
    ):
        vehicles = sorted(
            self._movement_vehicles(movement),
            key=lambda vehicle: vehicle.position,
            reverse=True,
        )
        if not vehicles:
            return

        green = self._axis_has_green(axis_name, phase)
        leader: Vehicle | None = None

        for vehicle in vehicles:
            already_crossing = (
                vehicle.position > self.stop_line_position_m
            )

            if leader is None:
                limit = (
                    self.exit_position_m
                    if green or already_crossing
                    else self.stop_line_position_m
                )
            else:
                leader_gap_limit = (
                    leader.position
                    - leader.length_m
                    - self.min_gap_m
                )
                if green or already_crossing:
                    limit = leader_gap_limit
                else:
                    limit = min(
                        self.stop_line_position_m,
                        leader_gap_limit,
                    )

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

        for axis_name, movements in MOVEMENTS_BY_AXIS.items():
            for movement in movements:
                self._update_movement(
                    axis_name,
                    movement,
                    current_phase,
                )

        remaining: List[Vehicle] = []
        for vehicle in self.active_vehicles:
            if vehicle.position >= self.exit_position_m - 1e-9:
                vehicle.state = "COMPLETED"
                self.completed_vehicles_count += 1
                self.completed_vehicles_by_type[
                    vehicle.vehicle_type
                ] += 1
            else:
                remaining.append(vehicle)
        self.active_vehicles = remaining

        self.current_time = round(
            self.current_time + self.time_step_s,
            2,
        )
        return self.current_time < self.duration_s

    def queue_length(
        self,
        axis_name: str,
        movement: str | None = None,
    ) -> int:
        return sum(
            1
            for vehicle in self.active_vehicles
            if vehicle.origin_axis == axis_name
            and vehicle.state == "QUEUED"
            and (movement is None or vehicle.movement == movement)
        )

    def average_wait(
        self,
        axis_name: str | None = None,
        movement: str | None = None,
    ) -> float:
        vehicles = self.active_vehicles
        if axis_name is not None:
            vehicles = [
                v
                for v in vehicles
                if v.origin_axis == axis_name
            ]
        if movement is not None:
            vehicles = [
                v for v in vehicles if v.movement == movement
            ]
        if not vehicles:
            return 0.0
        return (
            sum(v.wait_time_s for v in vehicles)
            / len(vehicles)
        )

    def active_count_by_type(self, vehicle_type: str) -> int:
        return sum(
            1
            for vehicle in self.active_vehicles
            if vehicle.vehicle_type == vehicle_type
        )
