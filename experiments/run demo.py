"""
Script de Execução de Demonstração
Sergipe Traffic AI - Prova prática da primeira etapa (Seções 14 e 21)
"""

import os
import json
from src.sergipe_traffic_ai.traffic.demand import TrafficDemandSimulator
from src.sergipe_traffic_ai.metrics.telemetry import TelemetryCollector

def run_simulation_demo():
    print("=== [Sergipe Traffic AI] Iniciando Demonstração da Fonte de Dados ===")
    
    # 1. Tenta carregar o cenário estruturado de Aracaju criado anteriormente
    scenario_path = "scenarios/aracaju_barao_augusto.json"
    
    if os.path.exists(scenario_path):
        with open(scenario_path, "r", encoding="utf-8") as f:
            scenario_data = json.load(f)
        print(f"-> Cenário carregado com sucesso de: {scenario_path}")
    else:
        print("-> Arquivo de cenário não encontrado. Usando configuração padrão em memória.")
        scenario_data = {
            "scenario": {
                "id": "aracaju_barao_augusto_v1",
                "seed": 42,
                "duration_s": 30.0,
                "time_step_s": 0.2,
                "demand": {
                    "axis_barao_maynard_rate": 0.85,
                    "axis_augusto_franco_rate": 0.75
                }
            }
        }

    # 2. Instancia o simulador de demanda e o coletor de telemetria
    simulator = TrafficDemandSimulator(scenario_data)
    telemetry = TelemetryCollector()

    print(f"-> Semente aleatória (Seed) configurada: {simulator.seed}")
    print(f"-> Taxas de chegada (Aracaju): Barão/Maynard = {simulator.rate_barao_maynard}, Augusto Franco = {simulator.rate_augusto_franco}")
    print("-> Executando passos de simulação e gerando dados sintéticos...")

    # 3. Loop de execução da simulação
    running = True
    step_count = 0
    
    while running:
        # Gera novos veículos sintéticos com base nas taxas e na semente
        new_vehicles = simulator.generate_vehicles_step()
        
        # Simula o estado dinâmico para fins de telemetria (Seção 14.3)
        current_phase = "BARAO_GREEN" if int(simulator.current_time * 5) % 2 == 0 else "AUGUSTO_GREEN"
        queue_barao = len([v for v in simulator.active_vehicles if "Barão" in v.origin_axis])
        queue_augusto = len([v for v in simulator.active_vehicles if "Augusto" in v.origin_axis])
        avg_wait = sum(v.wait_time_s for v in simulator.active_vehicles) / max(1, len(simulator.active_vehicles))
        
        # Registra os dados do passo atual no coletor de telemetria
        telemetry.record_step(
            time_s=simulator.current_time,
            phase=current_phase,
            queue_barao=queue_barao,
            queue_augusto=queue_augusto,
            avg_wait_s=avg_wait,
            vehicles_completed=simulator.completed_vehicles_count,
            controller_action="KEEP"
        )

        # Avança o tempo do simulador (retorna False se atingir a duração máxima)
        running = simulator.step()
        step_count += 1
        
        # Limitando para 30 segundos nesta demonstração rápida de execução
        if simulator.current_time >= 30.0:
            break

    print(f"-> Simulação finalizada com sucesso! Total de passos processados: {step_count}")
    print(f"-> Total de veículos sintéticos gerados no período: {len(simulator.active_vehicles)}")

    # 4. Exporta a telemetria gerada para arquivos locais (CSV e JSON) (Seção 14.4)
    output_dir = "experiments/output"
    os.makedirs(output_dir, exist_ok=True)
    
    csv_filepath = os.path.join(output_dir, "telemetria_aracaju_demo.csv")
    json_filepath = os.path.join(output_dir, "telemetria_aracaju_demo.json")
    
    telemetry.export_to_csv(csv_filepath)
    telemetry.export_to_json(json_filepath)
    print("=== Demonstração da Fonte de Dados Concluída com Sucesso ===")

if __name__ == "__main__":
    run_simulation_demo()