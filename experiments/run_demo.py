import os
import sys
import json

# Adiciona o diretório 'src' ao path do Python para encontrar o pacote localmente
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from sergipe_traffic_ai.traffic.demand import TrafficDemandSimulator
from sergipe_traffic_ai.metrics.telemetry import TelemetryCollector

def run_simulation_demo():
    print("=== [Sergipe Traffic AI] Iniciando Demonstração da Fonte de Dados ===")
    scenario_path = "scenarios/aracaju_barao_augusto.json"
    
    # Usando 'utf-8-sig' para ignorar o BOM opcional do PowerShell
    with open(scenario_path, "r", encoding="utf-8-sig") as f:
        scenario_data = json.load(f)
    print(f"-> Cenário carregado com sucesso de: {scenario_path}")

    simulator = TrafficDemandSimulator(scenario_data)
    telemetry = TelemetryCollector()

    print(f"-> Semente aleatória (Seed) configurada: {simulator.seed}")
    print(f"-> Taxas de chegada (Aracaju): Barão/Maynard = {simulator.rate_barao_maynard}, Augusto Franco = {simulator.rate_augusto_franco}")
    print("-> Executando passos de simulação e gerando dados sintéticos...")

    running = True
    step_count = 0
    
    while running:
        simulator.generate_vehicles_step()
        current_phase = "BARAO_GREEN" if int(simulator.current_time * 5) % 2 == 0 else "AUGUSTO_GREEN"
        queue_barao = len([v for v in simulator.active_vehicles if "Barão" in v.origin_axis])
        queue_augusto = len([v for v in simulator.active_vehicles if "Augusto" in v.origin_axis])
        avg_wait = sum(v.wait_time_s for v in simulator.active_vehicles) / max(1, len(simulator.active_vehicles))
        
        telemetry.record_step(
            time_s=simulator.current_time,
            phase=current_phase,
            queue_barao=queue_barao,
            queue_augusto=queue_augusto,
            avg_wait_s=avg_wait,
            vehicles_completed=simulator.completed_vehicles_count,
            controller_action="KEEP"
        )

        running = simulator.step()
        step_count += 1
        
        if simulator.current_time >= 30.0:
            break

    print(f"-> Simulação finalizada! Total de passos: {step_count}")
    print(f"-> Total de veículos sintéticos gerados: {len(simulator.active_vehicles)}")

    output_dir = "experiments/output"
    os.makedirs(output_dir, exist_ok=True)
    
    telemetry.export_to_csv(os.path.join(output_dir, "telemetria_aracaju_demo.csv"))
    telemetry.export_to_json(os.path.join(output_dir, "telemetria_aracaju_demo.json"))
    print("=== Demonstração da Fonte de Dados Concluída com Sucesso ===")

if __name__ == "__main__":
    run_simulation_demo()
