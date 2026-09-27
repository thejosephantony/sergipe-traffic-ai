# Check-in 2 — Dados, pré-processamento e baseline

Este documento organiza a demonstração exigida no **Check-in 2** do Sergipe Traffic AI.

## O que precisa ser demonstrado

1. **Fonte de dados (datasets/APIs)**;
2. **Estratégia de limpeza/pré-processamento**;
3. **Modelo baseline pretendido**.

O protótipo atual usa uma estratégia híbrida:

- **geografia oficial:** APIs de Malhas Territoriais do IBGE;
- **rede viária:** OpenStreetMap está planejado para a próxima ingestão;
- **demanda de tráfego atual:** sintética, controlada e reproduzível por seed.

> As taxas de chegada, a divisão entre sentidos e a composição carro/moto/ônibus são parâmetros sintéticos. Eles não devem ser apresentados como contagens reais de Aracaju.

## Fontes

### IBGE — Sergipe

- UF: **28**
- uso: contorno estadual/contextualização geográfica;
- API: `https://servicodados.ibge.gov.br/api/v3/malhas/estados/28?formato=application/vnd.geo+json&qualidade=minima`

### IBGE — Aracaju

- município: **2800308**
- uso: recorte municipal/contextualização do cenário piloto;
- API: `https://servicodados.ibge.gov.br/api/v3/malhas/municipios/2800308?formato=application/vnd.geo+json&qualidade=minima`

### OpenStreetMap

- uso futuro: rede viária, sentidos e atributos das vias;
- licença: **ODbL 1.0**;
- atribuição exigida: **© OpenStreetMap contributors**.

### Demanda sintética

Arquivo atual:

`scenarios/aracaju_barao_augusto.json`

Ele registra:

- seed;
- duração;
- timestep;
- taxas de chegada;
- composição da frota;
- divisão por sentido;
- parâmetros do controlador.

## Pipeline de pré-processamento

O pipeline executa:

1. validação da estrutura do cenário;
2. validação das taxas;
3. normalização da composição da frota;
4. normalização da divisão por sentido;
5. derivação das taxas por movimento;
6. cálculo de intervalo médio entre chegadas;
7. registro da seed;
8. registro da proveniência;
9. geração de um cenário pré-processado;
10. geração de um relatório do Check-in 2.

Quando `--fetch-geography` é usado, ele também:

1. baixa GeoJSON do IBGE;
2. valida `FeatureCollection`;
3. identifica os tipos de geometria;
4. verifica presença de coordenadas;
5. calcula bounding box em longitude/latitude;
6. preserva o arquivo bruto para rastreabilidade.

## Como demonstrar

No PowerShell, na raiz do projeto:

```powershell
python -m sergipe_traffic_ai.data_pipeline.checkin2
```

Isso cria:

- `experiments/output/checkin2/preprocessed_scenario.json`;
- `experiments/output/checkin2/checkin2_report.json`.

Para tentar baixar as malhas oficiais do IBGE:

```powershell
python -m sergipe_traffic_ai.data_pipeline.checkin2 --fetch-geography
```

Se a rede estiver indisponível, o pipeline registra a falha e mantém a demonstração dos dados sintéticos funcionando.

## Baseline

O baseline é o **controlador semafórico de tempo fixo**.

Ele:

- não usa Machine Learning;
- segue ciclo predeterminado;
- inclui verde, amarelo e todos-vermelhos;
- serve como referência para medir se estratégias futuras realmente melhoram o desempenho.

Demonstração:

```powershell
python experiments/run_baseline_experiment.py
```

Depois, o protótipo visual:

```powershell
python -m sergipe_traffic_ai.visual.app
```

Use a tecla **D** para abrir o resumo de **Dados & Pré-processamento** durante a apresentação.

## Roteiro de fala curto

> O projeto usa uma estratégia híbrida de dados. Para a geografia, usamos fontes oficiais do IBGE e planejamos integrar a rede viária do OpenStreetMap. Nesta etapa, a demanda veicular é sintética e reproduzível por seed, porque ainda não estamos afirmando possuir contagens reais do cruzamento. O pipeline valida e normaliza esses parâmetros, deriva taxas por sentido e registra a proveniência. Como referência experimental, usamos um controlador de tempo fixo sem IA. Nas etapas seguintes, esse baseline será comparado com controladores adaptativos e com Reinforcement Learning.
