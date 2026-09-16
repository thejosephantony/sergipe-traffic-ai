import os
import sys
import json

# Adiciona o diretório 'src' ao path do Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from sergipe_traffic_ai.controllers.rl_environment import TrafficRLEnvironment

def run_rl_environment_test():
    print("=== [Sergipe Traffic AI] Testando o Ambiente de Aprendizado por Reforço ===")
    
    # Carrega o cenário de Aracaju
    scenario_path = "scenarios/aracaju_barao_augusto.json"
    with open(scenario_path, "r", encoding="utf-8-sig") as f:
        scenario_data = json.load(f)

    # Inicializa o ambiente RL compatível (Seção 27.2)
    env = TrafficRLEnvironment(scenario_data)
    
    # 1. Testa o método reset
    obs = env.reset()
    print(f"-> Ambiente resetado com sucesso. Observação inicial: {obs}")

    done = False
    step_count = 0
    total_reward = 0.0

    print("-> Simulando passos com ações aleatórias (Agente simulado)...")
    
    while not done and step_count < 50:
        # Simula uma política simples: escolhe ação 0 (manter) ou 1 (trocar) alternadamente
        action = 1 if step_count % 15 == 0 else 0
        
        obs, reward, done, info = env.step(action)
        total_reward += reward
        step_count += 1
        
        if step_count % 10 == 0:
            print(f"   Passo {step_count} | Fase: {env.current_phase} | Ação: {action} | Recompensa do passo: {reward} | Filas (Barão/Augusto): {obs['queue_barao']}/{obs['queue_augusto']}")

    print(f"-> Teste do ambiente concluído em {step_count} passos.")
    print(f"-> Recompensa acumulada no episódio de teste: {round(total_reward, 2)}")
    print("=== Ambiente de RL validado e pronto para integração com algoritmos (como Q-Learning ou DQN) ===")

if __name__ == "__main__":
    run_rl_environment_test()
