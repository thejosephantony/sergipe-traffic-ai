# Sergipe Traffic AI 🚦

Laboratório virtual de Inteligência Artificial para simulação de trânsito e avaliação de estratégias de controle semafórico em cenários urbanos inspirados em Sergipe.

## Objetivo

Comparar controladores semafóricos **fixos**, **adaptativos** e, em fases posteriores, baseados em **Reinforcement Learning**, medindo impacto sobre tempo de espera, tamanho de filas, throughput e fluidez do tráfego.

## Estado atual

**v0.3 — protótipo visual funcional / preparação experimental**

- simulador discreto reproduzível por seed;
- tráfego bidirecional com carros, motos e ônibus;
- parada antes da faixa de pedestres;
- fases verde, amarelo e todos-vermelhos;
- controlador de tempo fixo (baseline);
- controlador adaptativo heurístico;
- telemetria e métricas;
- visualização Pygame com dashboard e áudio opcional;
- pipeline de dados do Check-in 2;
- integração da rede viária do OpenStreetMap via Overpass API;
- testes automatizados e workflow de CI.

> O controlador adaptativo atual é baseado em regras. O controlador com IA/RL ainda é uma etapa posterior do projeto.

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

## Executar o protótipo visual

```powershell
python -m sergipe_traffic_ai.visual.app
```

Controles principais:

- `ESPAÇO`: pausa;
- `R`: reset;
- `1`: baseline fixo;
- `2`: adaptativo por regras;
- `D`: tela de Dados & Pré-processamento do Check-in 2;
- `G`: alterna entre mapa OpenStreetMap e visual esquemático;
- `M`: liga/desliga áudio;
- `↑ / ↓`: velocidade da simulação.

Quando `experiments/output/checkin2/osm/osm_road_network.geojson` existe, o Pygame inicia no **modo OSM**. A rede viária real é projetada para a área de simulação e os veículos são orientados pelos eixos identificados no OpenStreetMap.

## Check-in 2 — dados e pré-processamento

Execute:

```powershell
python -m sergipe_traffic_ai.data_pipeline.checkin2
```

Para baixar e pré-processar a rede viária do OpenStreetMap:

```powershell
python -m sergipe_traffic_ai.data_pipeline.checkin2 --fetch-osm
```

Para executar IBGE + OSM na mesma demonstração:

```powershell
python -m sergipe_traffic_ai.data_pipeline.checkin2 --fetch-geography --fetch-osm
```

A integração OSM usa a Overpass API e gera um GeoJSON local com geometria e atributos como nome, tipo de via, sentido, número de faixas e velocidade máxima quando esses campos existem no OSM. Esse GeoJSON também é usado pelo Pygame como camada cartográfica quando disponível.

O pipeline gera um relatório rastreável em `experiments/output/checkin2/`. A demanda veicular continua sintética nesta etapa; o OSM fornece a rede viária, não contagens de tráfego.

Consulte `docs/CHECKIN2.md` para o roteiro completo da apresentação.

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
