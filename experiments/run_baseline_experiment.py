import os
import sys
import json

# Adiciona o diretório 'src' ao path do Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from sergipe_traffic_ai.traffic.demand import TrafficDemandSimulator
from sergipe_traffic_ai.controllers.fixed_controller import FixedTrafficController
from sergipe_traffic_ai.metrics.telemetry import TelemetryCollector

def run_baseline_experiment():
    print("=== [Sergipe Traffic AI] Executando Experimento com Baseline (Tempo Fixo) ===")
    
    scenario_path = "scenarios/aracaju_barao_augusto.json"
    with open(scenario_path, "r", encoding="utf-8-sig") as f:
        scenario_data = json.load(f)
    print(f"-> Cenário carregado: {scenario_path}")

    # Inicializa simulador, controlador baseline e coletor de telemetria
    simulator = TrafficDemandSimulator(scenario_data)
    controller = FixedTrafficController()
    telemetry = TelemetryCollector()

    controller.reset(scenario_data)
    simulator.reset()

    print(f"-> Semente (Seed): {simulator.seed} | Controlador: Fixo (Baseline)")
    print("-> Iniciando simulação do cruzamento (Barão/Maynard x Augusto Franco)...")

    running = True
    step_count = 0
    
    while running:
        # Gera demanda do passo
        simulator.generate_vehicles_step()
        
        # Consulta o controlador baseline para definir a fase atual com base no relógio (Seção 10.2)
        current_phase = controller.decide({}, simulator.current_time)
        
        # Computa métricas simuladas do passo
        queue_barao = len([v for v in simulator.active_vehicles if "Barão" in v.origin_axis])
        queue_augusto = len([v for v in simulator.active_vehicles if "Augusto" in v.origin_axis])
        
        # Simula o tempo de espera acumulado dos veículos na fila
        for v in simulator.active_vehicles:
            if v.state == "MOVING":
                v.wait_time_s = round(v.wait_time_s + simulator.time_step_s, 2)

        avg_wait = sum(v.wait_time_s for v in simulator.active_vehicles) / max(1, len(simulator.active_vehicles))
        
        # Registra telemetria (Seção 14.3)
        telemetry.record_step(
            time_s=simulator.current_time,
            phase=current_phase,
            queue_barao=queue_barao,
            queue_augusto=queue_augusto,
            avg_wait_s=avg_wait,
            vehicles_completed=simulator.completed_vehicles_count,
            controller_action=current_phase
        )

        # Avança o tempo
        running = simulator.step()
        step_count += 1
        
        # Executa por 60 segundos de simulação para a demonstração
        if simulator.current_time >= 60.0:
            break

    print(f"-> Experimento finalizado! Total de passos: {step_count}")
    print(f"-> Total de veículos gerados: {len(simulator.active_vehicles)}")
    print(f"-> Tempo médio de espera final (Baseline): {round(avg_wait, 2)} segundos")

    # Exporta resultados do baseline para a pasta de experimentos (Seção 14.4)
    output_dir = "experiments/output"
    os.makedirs(output_dir, exist_ok=True)
    
    telemetry.export_to_csv(os.path.join(output_dir, "telemetria_baseline_fixed.csv"))
    telemetry.export_to_json(os.path.join(output_dir, "telemetria_baseline_fixed.json"))
    print("=== Relatório de Telemetria do Baseline Salvo com Sucesso ===")

if __name__ == "__main__":
    run_baseline_experiment()
