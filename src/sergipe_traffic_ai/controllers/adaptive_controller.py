"""
Controlador Semafórico Adaptativo Baseado em Regras
Sergipe Traffic AI - Seção 11
"""

class AdaptiveTrafficController:
    """
    Controlador adaptativo que calcula prioridades com base nas filas
    e no tempo de espera para decidir a troca de fase (Seção 11).
    """
    def __init__(self, min_green_s: float = 10.0, max_green_s: float = 60.0, 
                 alpha: float = 1.0, beta: float = 0.5):
        self.min_green_s = min_green_s
        self.max_green_s = max_green_s
        self.alpha = alpha  # Peso para o tamanho da fila
        self.beta = beta    # Peso para o tempo de espera
        
        self.current_phase = "BARAO_GREEN"
        self.time_in_current_phase = 0.0

    def reset(self, scenario):
        """Reinicia o controlador para o estado inicial do episódio."""
        self.current_phase = "BARAO_GREEN"
        self.time_in_current_phase = 0.0

    def decide(self, observation: dict, now: float) -> str:
        """
        Calcula a pontuação de prioridade para cada eixo com base em regras
        explícitas e decide se mantém ou alterna a fase (Seção 11.2).
        """
        queue_barao = observation.get("queue_barao", 0)
        queue_augusto = observation.get("queue_augusto", 0)
        wait_barao = observation.get("wait_barao", 0.0)
        wait_augusto = observation.get("wait_augusto", 0.0)

        # Cálculo da pontuação de prioridade (Score = alpha * fila + beta * espera)
        score_barao = (self.alpha * queue_barao) + (self.beta * wait_barao)
        score_augusto = (self.alpha * queue_augusto) + (self.beta * wait_augusto)

        # Atualiza o tempo decorrido na fase atual
        self.time_in_current_phase += observation.get("time_step_s", 0.2)

        # Regras de transição com respeito ao tempo mínimo de verde (Segurança lógica - Seção 9.4 e 11.3)
        if self.time_in_current_phase >= self.min_green_s:
            if self.current_phase == "BARAO_GREEN":
                # Se o eixo Augusto Franco estiver com prioridade muito maior ou atingiu o teto
                if score_augusto > score_barao or self.time_in_current_phase >= self.max_green_s:
                    self.current_phase = "AUGUSTO_GREEN"
                    self.time_in_current_phase = 0.0
            else:
                if score_barao > score_augusto or self.time_in_current_phase >= self.max_green_s:
                    self.current_phase = "BARAO_GREEN"
                    self.time_in_current_phase = 0.0

        return self.current_phase

    def on_transition(self, previous_phase: str, new_phase: str):
        pass