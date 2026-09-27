import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from sergipe_traffic_ai.controllers.adaptive_controller import AdaptiveTrafficController
from sergipe_traffic_ai.metrics.telemetry import TelemetryCollector
from sergipe_traffic_ai.traffic.demand import (
    AUGUSTO_AXIS,
    BARAO_AXIS,
    TrafficDemandSimulator,
)


def run_adaptive_experiment():
    print("=== [Sergipe Traffic AI] Controlador Adaptativo ===")

    scenario_path = "scenarios/aracaju_barao_augusto.json"
    with open(scenario_path, "r", encoding="utf-8-sig") as file:
        scenario_data = json.load(file)

    simulator = TrafficDemandSimulator(scenario_data)
    controller = AdaptiveTrafficController()
    telemetry = TelemetryCollector()

    controller.reset(scenario_data)
    simulator.reset()

    print(f"-> Semente: {simulator.seed} | Controlador: Adaptativo")
    print("-> Executando dinâmica causal do cruzamento piloto...")

    while simulator.current_time < 60.0:
        simulator.generate_vehicles_step()

        observation = {
            "queue_barao": simulator.queue_length(BARAO_AXIS),
            "queue_augusto": simulator.queue_length(AUGUSTO_AXIS),
            "wait_barao": simulator.average_wait(BARAO_AXIS),
            "wait_augusto": simulator.average_wait(AUGUSTO_AXIS),
            "time_step_s": simulator.time_step_s,
        }

        current_phase = controller.decide(observation, simulator.current_time)
        simulator.step(current_phase)

        telemetry.record_step(
            time_s=simulator.current_time,
            phase=current_phase,
            queue_barao=simulator.queue_length(BARAO_AXIS),
            queue_augusto=simulator.queue_length(AUGUSTO_AXIS),
            avg_wait_s=simulator.average_wait(),
            vehicles_completed=simulator.completed_vehicles_count,
            controller_action=current_phase,
        )

    print(f"-> Veículos gerados: {simulator.vehicle_counter}")
    print(f"-> Veículos concluídos: {simulator.completed_vehicles_count}")
    print(f"-> Espera média final: {simulator.average_wait():.2f} s")

    output_dir = "experiments/output"
    os.makedirs(output_dir, exist_ok=True)
    telemetry.export_to_csv(os.path.join(output_dir, "telemetria_adaptive.csv"))
    telemetry.export_to_json(os.path.join(output_dir, "telemetria_adaptive.json"))
    print("=== Telemetria adaptativa salva com sucesso ===")


if __name__ == "__main__":
    run_adaptive_experiment()
