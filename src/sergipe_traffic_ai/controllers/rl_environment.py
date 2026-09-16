"""
Ambiente de Aprendizado por Reforço para o Controle Semafórico
Sergipe Traffic AI - Seções 12, 13 e 27
"""

from typing import Dict, Any, Tuple
from sergipe_traffic_ai.traffic.demand import TrafficDemandSimulator

class TrafficRLEnvironment:
    """
    Expõe o simulador como um ambiente de Aprendizado por Reforço,
    definindo estado, ações, recompensas e restrições de segurança (Seção 12 e 27).
    """
    def __init__(self, scenario_config: Dict[str, Any]):
        self.simulator = TrafficDemandSimulator(scenario_config)
        self.current_phase = "BARAO_GREEN"
        self.time_in_phase = 0.0
        self.min_green_s = 10.0  # Restrição de segurança lógica (Seção 9.3 e 13.4)

    def reset(self) -> Dict[str, float]:
        """Reseta o ambiente para o início de um novo episódio (Seção 27.2)."""
        self.simulator.reset()
        self.current_phase = "BARAO_GREEN"
        self.time_in_phase = 0.0
        return self._get_observation()

    def _get_observation(self) -> Dict[str, float]:
        """Constrói o vetor de estado observável pelo agente (Seção 12.2)."""
        queue_barao = len([v for v in self.simulator.active_vehicles if "Barão" in v.origin_axis])
        queue_augusto = len([v for v in self.simulator.active_vehicles if "Augusto" in v.origin_axis])
        
        return {
            "queue_barao": float(queue_barao),
            "queue_augusto": float(queue_augusto),
            "phase_encoded": 1.0 if self.current_phase == "BARAO_GREEN" else 0.0,
            "time_in_phase": self.time_in_phase
        }

    def step(self, action: int) -> Tuple[Dict[str, float], float, bool, Dict[str, Any]]:
        """
        Executa uma ação no ambiente:
        Ação 0: Manter a fase atual.
        Ação 1: Solicitar troca de fase (sujeita a máscara de segurança).
        """
        # Geração de demanda do passo
        self.simulator.generate_vehicles_step()
        self.time_in_phase = round(self.time_in_phase + self.simulator.time_step_s, 2)

        # Máscara de ações / Restrição de segurança lógica (Seção 13.4 e 27.2)
        if action == 1 and self.time_in_phase >= self.min_green_s:
            # Realiza a transição segura de fase
            self.current_phase = "AUGUSTO_GREEN" if self.current_phase == "BARAO_GREEN" else "BARAO_GREEN"
            self.time_in_phase = 0.0

        # Cálculo de métricas e penalidades para a função de recompensa (Seção 12.4)
        queue_barao = len([v for v in self.simulator.active_vehicles if "Barão" in v.origin_axis])
        queue_augusto = len([v for v in self.simulator.active_vehicles if "Augusto" in v.origin_axis])
        total_queue = queue_barao + queue_augusto

        # Recompensa negativa baseada no tamanho total da fila (penaliza atrasos)
        reward = -1.0 * float(total_queue)

        # Avança o tempo do simulador
        is_running = self.simulator.step()
        done = not is_running

        obs = self._get_observation()
        info = {"completed_vehicles": self.simulator.completed_vehicles_count}

        return obs, reward, done, info