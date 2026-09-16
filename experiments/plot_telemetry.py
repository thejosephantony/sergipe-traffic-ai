import os
import pandas as pd
import matplotlib.pyplot as plt

def plot_baseline_telemetry():
    print("=== [Sergipe Traffic AI] Gerando Gráfico de Telemetria (Baseline) ===")
    
    csv_path = "experiments/output/telemetria_baseline_fixed.csv"
    
    if not os.path.exists(csv_path):
        print(f"Erro: Arquivo de telemetria não encontrado em {csv_path}. Execute o baseline primeiro.")
        return
        
    # Carrega os dados tabulares utilizando Pandas (Seção 14.4 e 21.2)
    df = pd.read_csv(csv_path)
    
    # Configuração do gráfico usando Matplotlib (Seção 21.2)
    plt.figure(figsize=(10, 5))
    plt.plot(df['time_s'], df['queue_barao_maynard'], label='Fila: Av. Barão de Maruim / Maynard', color='blue', linewidth=2)
    plt.plot(df['time_s'], df['queue_augusto_franco'], label='Fila: Av. Augusto Franco', color='orange', linewidth=2)
    
    plt.xlabel('Tempo de Simulação (s)')
    plt.ylabel('Tamanho da Fila (Veículos)')
    plt.title('Evolução Dinâmica das Filas - Controlador Fixo (Baseline - Aracaju)')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    
    # Salva a imagem do gráfico na pasta de experimentos
    output_dir = "experiments/output"
    os.makedirs(output_dir, exist_ok=True)
    output_plot_path = os.path.join(output_dir, "baseline_queues_chart.png")
    
    plt.savefig(output_plot_path, dpi=300, bbox_inches='tight')
    print(f"-> Gráfico salvo com sucesso em: {output_plot_path}")
    
    # Exibe o gráfico na tela
    plt.show()

if __name__ == "__main__":
    plot_baseline_telemetry()
