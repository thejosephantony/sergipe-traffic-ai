# Sergipe Traffic AI 🚦

**Laboratório virtual de simulação de trânsito e aprendizado por reforço**, inspirado em um cruzamento urbano de Aracaju, Sergipe.

O objetivo do projeto é estudar e comparar estratégias de controle semafórico por meio de uma simulação reproduzível, utilizando indicadores de filas, tempo de espera e veículos concluídos.

> **Fase atual: v0.7 do roadmap — Q-Learning implementado; avaliação comparativa em andamento.** Este número representa uma etapa do roadmap acadêmico, não a versão do pacote Python (atualmente `0.1.0`).

## Estado do projeto

| Componente | Situação |
| --- | --- |
| Simulador de tráfego bidirecional (carros, motos e ônibus) | Implementado |
| Controlador semafórico de tempo fixo (baseline) | Implementado |
| Controlador adaptativo **por regras** | Implementado — não é aprendizado de máquina |
| Ambiente de Reinforcement Learning | Implementado em versão inicial |
| Agente de **Q-Learning tabular** | Implementado e treinável |
| Treinamento, Q-table em JSON e avaliação sem exploração | Implementados |
| Comparação científica entre fixo × adaptativo × Q-Learning | **Pendente de consolidação** |
| Visualização Pygame, métricas e painel OSM | Implementados |
| Pedestres, ciclistas, ciclovia e veículos de emergência | **Planejados para v0.8; ainda não implementados** |

**Importante:** ter um agente que aprende não significa que ele já superou o baseline. Qualquer conclusão de desempenho exige experimentos controlados com múltiplas seeds e métricas comparáveis. A demanda veicular atual é **sintética**, e o cenário ainda não foi calibrado com contagens de tráfego reais.

## Cenário e dados

O cenário piloto é inspirado nos eixos **Avenida Augusto Franco** e **Avenida Desembargador Maynard / Barão de Maruim**, em Aracaju/SE. A referência geográfica é aproximada; o protótipo não é uma reprodução topográfica ou geométrica exata da interseção.

- **IBGE:** contexto territorial de Sergipe e Aracaju, obtido opcionalmente no pipeline.
- **OpenStreetMap / Overpass API:** geometria e atributos da rede viária do entorno, quando disponíveis.
- **Demanda sintética:** geração de veículos, composição da frota e divisão por sentido, com seeds reproduzíveis.

O Pygame mantém um **cruzamento esquemático ampliado** para mostrar faixas, filas e semáforos. Quando o GeoJSON do OSM está disponível, ele aparece em um **painel cartográfico contextual**; os veículos da simulação não percorrem necessariamente as geometrias reais do OSM.

## Instalação

Requisitos: **Python 3.11 ou superior**, Git e PowerShell no Windows.

Na raiz do repositório, no **Windows PowerShell**:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
```

Em Linux/macOS, ative o ambiente com `source .venv/bin/activate` antes da instalação.

> Caso o comando `pytest` não seja reconhecido ou apareça `ModuleNotFoundError: No module named 'sergipe_traffic_ai'`, ative o ambiente virtual e execute a instalação editável acima. Prefira `python -m pytest`.

## Executar a simulação visual

```powershell
python -m sergipe_traffic_ai.visual.app
```

| Tecla | Ação |
| --- | --- |
| `1` | Controlador fixo (baseline) |
| `2` | Controlador adaptativo por regras |
| `3` | Controlador Q-Learning **com modelo treinado** |
| `ESPAÇO` | Pausar/continuar |
| `R` | Reiniciar a simulação |
| `D` | Abrir/fechar a tela de dados do Check-in 2 |
| `G` | Mostrar/ocultar o painel contextual OSM |
| `M` | Ligar/desligar o áudio |
| `↑` / `↓` | Aumentar/reduzir a velocidade |

**Trocar entre os modos `1`, `2` e `3` reinicia o episódio**, impedindo que um novo controlador assuma uma fase incompatível com a anterior. O modo `3` requer o arquivo `models/q_learning_aracaju.json`, gerado pelo treinamento.

### Regras de circulação e segurança

O protótipo considera sentidos de circulação independentes, filas por aproximação e distância longitudinal mínima entre veículos. Os sprites foram redimensionados para acompanhar essa escala e reduzir sobreposições **na mesma faixa**.

As mudanças de verde seguem uma sequência determinística:

```text
VERDE → AMARELO → TODOS VERMELHOS → VERDE DO EIXO OPOSTO
```

No cenário piloto, o amarelo dura **4 s** e todos-vermelhos dura **no mínimo 2 s**. Se ainda houver veículos que passaram da linha de retenção, o sistema mantém ambos os eixos bloqueados até a saída deles da área simulada. Essa regra vale para os três controladores.

Essas salvaguardas pertencem a um **modelo simplificado**: não substituem um detector físico de colisões, modelagem detalhada de pedestres ou validação de segurança viária real.

## Q-Learning — treinamento e avaliação

O controlador inteligente emprega **Q-Learning tabular**, com:

- **Estado:** categorias de filas dos dois eixos, fase semafórica e tempo na fase;
- **Ações:** `0 = manter` e `1 = solicitar troca`;
- **Recompensa:** penalidades para fila e espera, incentivo ao throughput e custo de troca;
- **Exploração:** política epsilon-greedy durante treinamento;
- **Segurança:** o agente solicita mudanças, mas não controla diretamente o amarelo ou todos-vermelhos.

**Treinamento rápido para verificar a execução:**

```powershell
python experiments/train_q_learning.py --episodes 20 --duration 300
```

**Treinamento padrão** (200 episódios de 600 s simulados, com seeds consecutivas):

```powershell
python experiments/train_q_learning.py
```

Arquivos gerados localmente:

```text
models/q_learning_aracaju.json
experiments/output/q_learning/training_history.csv
```

**Avaliação da política aprendida, sem exploração (`epsilon=0`):**

```powershell
python experiments/evaluate_q_learning.py
```

Por padrão, a avaliação utiliza **20 seeds**, começando em 1000, e salva os resultados em `experiments/output/q_learning/evaluation.csv`.

**Atenção:** após mudanças na lógica do simulador ou dos tempos semafóricos, execute novamente treinamento e avaliação. Uma Q-table antiga pode ser carregada, mas foi aprendida sob condições anteriores.

O script atual avalia o **Q-Learning isoladamente**. A comparação definitiva **fixo × adaptativo × Q-Learning**, executada sobre as mesmas seeds, durações e cenários, ainda é uma tarefa da v0.7.

Metodologia completa: [docs/Q_LEARNING.md](docs/Q_LEARNING.md).

## Pipeline de dados — Check-in 2

Gerar arquivos do cenário e relatório de pré-processamento:

```powershell
python -m sergipe_traffic_ai.data_pipeline.checkin2
```

Buscar a rede viária do OSM (requer conexão à internet e disponibilidade da API):

```powershell
python -m sergipe_traffic_ai.data_pipeline.checkin2 --fetch-osm
```

Consultar também as fontes geográficas do IBGE:

```powershell
python -m sergipe_traffic_ai.data_pipeline.checkin2 --fetch-geography --fetch-osm
```

O pipeline salva os resultados em `experiments/output/checkin2/`. O GeoJSON esperado pelo Pygame fica em `experiments/output/checkin2/osm/osm_road_network.geojson`.

Os dados de rede viária **não fornecem contagens reais de veículos**; a demanda continua sintética.

Documentação do Check-in: [docs/CHECKIN2.md](docs/CHECKIN2.md).

## Roadmap acadêmico

Os marcos representam a evolução funcional do projeto, não necessariamente releases publicados.

| Fase | Objetivo | Situação |
| --- | --- | --- |
| **v0.1** | Núcleo do simulador e baseline | Implementado |
| **v0.2** | Tráfego bidirecional, veículos e métricas | Protótipo implementado |
| **v0.3** | Interface Pygame e telemetria | Implementado |
| **v0.4** | Experimentos automatizados e métricas comparáveis | Parcial; comparativo completo pendente |
| **v0.5** | Controle adaptativo | Heurística implementada |
| **v0.6** | Ambiente de Reinforcement Learning | Implementação inicial concluída |
| **v0.7 (atual)** | Q-Learning, treinamento e validação comparativa | Algoritmo implementado; validação pendente |
| **v0.8 (próxima)** | Mobilidade multimodal e infraestrutura urbana | Planejada |
| **v0.9** | Dashboard e experimentos ampliados | Planejada |
| **v1.0** | Análise final e apresentação acadêmica | Pendente |

### Próxima expansão proposta: v0.8 — Mobilidade multimodal

**Ainda não implementada.** A proposta é evoluir o cenário da Avenida Augusto Franco em etapas:

1. **Infraestrutura:** desenhar calçadas, ciclovia/faixa ciclável e pontos de travessia, mantendo a leitura do cruzamento.
2. **Ciclistas:** acrescentar agentes com movimento e parada na infraestrutura ciclável.
3. **Pedestres:** acrescentar espera e travessia controlada por fase semafórica.
4. **Emergências:** incluir ambulâncias, viaturas e/ou bombeiros com solicitação de prioridade, sempre respeitando transições seguras.

Antes de usar esses agentes para avaliar o Q-Learning, será necessário estender estados, ações/recompensas e métricas do ambiente e treinar novamente o agente.

## Estrutura principal

```text
scenarios/                         # Cenário e parâmetros sintéticos
src/sergipe_traffic_ai/
├── controllers/
│   ├── fixed_controller.py        # Baseline de tempo fixo
│   ├── adaptive_controller.py     # Heurística adaptativa
│   ├── q_learning.py              # Q-table e lógica de segurança
│   └── rl_environment.py          # Ambiente RL causal
├── traffic/demand.py              # Chegadas e dinâmica veicular
├── training/q_learning.py         # Loop de treinamento
├── data_pipeline/                 # IBGE, OSM e pré-processamento
└── visual/                        # Pygame, sprites e painel OSM
experiments/
├── train_q_learning.py
└── evaluate_q_learning.py
tests/                              # Testes automatizados
docs/                               # Documentação do projeto
```

## Qualidade e limitações

A CI executa `ruff check src tests` e `pytest -q` em Python 3.11. Para validar localmente:

```powershell
python -m pytest
python -m ruff check src tests
```

O Sergipe Traffic AI é um **ambiente experimental e acadêmico**. A rede do OSM fornece contexto geográfico, não demanda observada. As estratégias ainda precisam de avaliação estatística e calibração antes que qualquer resultado possa ser extrapolado para uma infraestrutura viária real.

Mais informações: [documentação de Q-Learning](docs/Q_LEARNING.md), [Check-in 2](docs/CHECKIN2.md), [visão do projeto](docs/PROJECT.md) e [roadmap detalhado](docs/ROADMAP.md).
