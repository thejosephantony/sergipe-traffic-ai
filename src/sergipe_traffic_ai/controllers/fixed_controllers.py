"""
Controlador Semafórico de Tempo Fixo (Baseline)
Sergipe Traffic AI - Seção 10
"""

class FixedTrafficController:
    """
    Controlador de tempo fixo que alterna as fases de acordo com um ciclo rígido,
    servindo como linha de base para comparação com estratégias inteligentes (Seção 10).
    """
    def __init__(self, green_duration_s: float = 30.0, yellow_duration_s: float = 3.0, all_red_s: float = 1.0):
        self.green_duration_s = green_duration_s
        self.yellow_duration_s = yellow_duration_s
        self.all_red_s = all_red_s
        
        # Duração total de uma subfase e do ciclo completo
        self.phase_time = self.green_duration_s + self.yellow_duration_s + self.all_red_s
        self.cycle_duration_s = self.phase_time * 2  # Eixo 1 (Barão) + Eixo 2 (Augusto Franco)
        
        self.current_phase = "BARAO_GREEN"

    def reset(self, scenario):
        """Reinicia o controlador para o estado inicial do episódio."""
        self.current_phase = "BARAO_GREEN"

    def decide(self, observation: dict, now: float) -> str:
        """
        Decide a fase semafórica com base exclusivamente no relógio da simulação,
        dividindo o tempo em intervalos fixos de ciclo (Seção 10.2).
        """
        # Determina em qual momento do ciclo atual o relógio se encontra
        time_in_cycle = now % self.cycle_duration_s
        
        if time_in_cycle < self.phase_time:
            # Primeira metade do ciclo: Libera o eixo Barão de Maruim / Des. Maynard
            self.current_phase = "BARAO_GREEN"
        else:
            # Segunda metade do ciclo: Libera o eixo Augusto Franco
            self.current_phase = "AUGUSTO_GREEN"
            
        return self.current_phase

    def on_transition(self, previous_phase: str, new_phase: str):
        """Callback executado quando ocorre uma transição de fase."""
        pass