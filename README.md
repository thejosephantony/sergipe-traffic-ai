# Sergipe Traffic AI 🚦

Laboratório virtual de Inteligência Artificial para simulação de trânsito e avaliação de estratégias de controle semafórico em cenários urbanos inspirados em Sergipe.

## Objetivo

Comparar controladores semafóricos **fixos**, **adaptativos** e, em fases posteriores, baseados em **Reinforcement Learning**, medindo impacto sobre tempo de espera, tamanho de filas, throughput e fluidez do tráfego.

## Estado atual

**v0.1 — MVP estrutural**

- domínio básico de veículos, vias, interseção e semáforos;
- simulador discreto simples e reproduzível;
- controlador de tempo fixo;
- controlador adaptativo heurístico;
- coleta de métricas;
- cenários configuráveis;
- testes automatizados;
- workflow de CI no GitHub Actions.

## Arquitetura

```text
src/sergipe_traffic_ai/
├── simulation/      # relógio e execução do ambiente
├── traffic/         # entidades do domínio
├── controllers/     # fixed, adaptive e futuro RL
├── metrics/         # coleta e consolidação de indicadores
└── scenarios/       # cenários experimentais
```

## Instalação

Requer Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
# .venv\\Scripts\\activate     # Windows
pip install -e .[dev]
```

## Executar o MVP

```bash
python -m sergipe_traffic_ai --controller fixed --steps 300 --seed 42
python -m sergipe_traffic_ai --controller adaptive --steps 300 --seed 42
```

Exemplo de saída:

```text
controller=adaptive
steps=300
vehicles_generated=...
vehicles_completed=...
average_wait=...
max_queue=...
throughput=...
```

## Testes

```bash
pytest
```

## Roadmap resumido

1. **v0.1** — núcleo do simulador e baseline;
2. **v0.2** — múltiplas faixas, rotas e telemetria;
3. **v0.3** — visualização 2D;
4. **v0.4** — experimentos automatizados;
5. **v0.5** — controlador adaptativo avançado;
6. **v0.6** — ambiente de Reinforcement Learning;
7. **v0.7** — Q-Learning/DQN/PPO;
8. **v0.8** — múltiplos cruzamentos e eventos;
9. **v0.9** — dashboard e IA generativa;
10. **v1.0** — avaliação final e demonstração acadêmica.

## Métricas principais

- tempo médio de espera;
- fila média e máxima;
- throughput;
- número de paradas;
- tempo total de viagem;
- velocidade média;
- atendimento de prioridades.

## Uso responsável

Este projeto é um **ambiente de pesquisa e simulação**. Resultados obtidos em ambiente virtual não devem ser interpretados como garantia de desempenho ou segurança em infraestrutura viária real.

## Documentação

Consulte [`docs/PROJECT.md`](docs/PROJECT.md) para a especificação inicial e [`docs/ROADMAP.md`](docs/ROADMAP.md) para o plano de desenvolvimento.
