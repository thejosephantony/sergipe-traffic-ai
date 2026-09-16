import os
import sys
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from sergipe_traffic_ai.traffic.demand import TrafficDemandSimulator
from sergipe_traffic_ai.controllers.adaptive_controller import AdaptiveTrafficController
from sergipe_traffic_ai.metrics.telemetry import TelemetryCollector

def run_adaptive_experiment():
    print("=== [Sergipe Traffic AI] Executando Experimento com Controlador Adaptativo ===")
    
    scenario_path = "scenarios/aracaju_barao_augusto.json"
    with open(scenario_path, "r", encoding="utf-8-sig") as f:
        scenario_data = json.load(f)

    simulator = TrafficDemandSimulator(scenario_data)
    controller = AdaptiveTrafficController()
    telemetry = TelemetryCollector()

    controller.reset(scenario_data)
    simulator.reset()

    print(f"-> Semente (Seed): {simulator.seed} | Controlador: Adaptativo por Regras")
    print("-> Executando simulação adaptativa no cruzamento de Aracaju...")

    running = True
    step_count = 0
    
    while running:
        simulator.generate_vehicles_step()
        
        queue_barao = len([v for v in simulator.active_vehicles if "Barão" in v.origin_axis])
        queue_augusto = len([v for v in simulator.active_vehicles if "Augusto" in v.origin_axis])
        
        for v in simulator.active_vehicles:
            if v.state == "MOVING":
                v.wait_time_s = round(v.wait_time_s + simulator.time_step_s, 2)

        avg_wait = sum(v.wait_time_s for v in simulator.active_vehicles) / max(1, len(simulator.active_vehicles))
        
        # Constrói o dicionário de observação exigido pelo controlador adaptativo
        observation = {
            "queue_barao": queue_barao,
            "queue_augusto": queue_augusto,
            "wait_barao": avg_wait,
            "wait_augusto": avg_wait,
            "time_step_s": simulator.time_step_s
        }
        
        current_phase = controller.decide(observation, simulator.current_time)
        
        telemetry.record_step(
            time_s=simulator.current_time,
            phase=current_phase,
            queue_barao=queue_barao,
            queue_augusto=queue_augusto,
            avg_wait_s=avg_wait,
            vehicles_completed=simulator.completed_vehicles_count,
            controller_action=current_phase
        )

        running = simulator.step()
        step_count += 1
        
        if simulator.current_time >= 60.0:
            break

    print(f"-> Experimento adaptativo finalizado! Total de passos: {step_count}")
    print(f"-> Tempo médio de espera final (Adaptativo): {round(avg_wait, 2)} segundos")

    output_dir = "experiments/output"
    os.makedirs(output_dir, exist_ok=True)
    telemetry.export_to_csv(os.path.join(output_dir, "telemetria_adaptive.csv"))
    telemetry.export_to_json(os.path.join(output_dir, "telemetria_adaptive.json"))
    print("=== Relatório de Telemetria do Controlador Adaptativo Salvo com Sucesso ===")

if __name__ == "__main__":
    run_adaptive_experiment()
