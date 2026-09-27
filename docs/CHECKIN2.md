# Check-in 2 — Dados, pré-processamento e baseline

Este documento organiza a demonstração exigida no **Check-in 2** do Sergipe Traffic AI.

## O que precisa ser demonstrado

1. **Fonte de dados (datasets/APIs)**;
2. **Estratégia de limpeza/pré-processamento**;
3. **Modelo baseline pretendido**.

O protótipo atual usa uma estratégia híbrida:

- **geografia oficial:** APIs de Malhas Territoriais do IBGE;
- **rede viária:** OpenStreetMap integrado via Overpass API;
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

- integração ativa via **Overpass API**;
- uso: rede viária real do entorno do cenário piloto;
- atributos tratados: geometria, `name`, `highway`, `oneway`, `lanes`, `maxspeed`, `surface`, entre outros quando disponíveis;
- consulta atual: raio de **800 m** ao redor do ponto de referência aproximado do cenário;
- licença: **ODbL 1.0**;
- atribuição: **© OpenStreetMap contributors**.

A geometria da via vem do OSM, mas **o volume de tráfego não**. As taxas de chegada dos veículos continuam sendo sintéticas nesta etapa.

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

Quando `--fetch-osm` é usado, ele:

1. consulta a Overpass API;
2. seleciona elementos `way` com tag `highway`;
3. reconstrói a geometria a partir dos nós OSM;
4. remove vias sem geometria utilizável;
5. normaliza `oneway`, `lanes` e `maxspeed`;
6. preserva nomes e categorias `highway`;
7. marca vias do cenário piloto por aliases de nome;
8. gera um GeoJSON processado;
9. gera um resumo com número de vias, tipos de `highway` e correspondências encontradas;
10. registra atribuição e licença ODbL.

## Como demonstrar

No PowerShell, na raiz do projeto:

```powershell
python -m sergipe_traffic_ai.data_pipeline.checkin2
```

Isso cria:

- `experiments/output/checkin2/preprocessed_scenario.json`;
- `experiments/output/checkin2/checkin2_report.json`.

Para baixar e processar a rede viária real do OpenStreetMap:

```powershell
python -m sergipe_traffic_ai.data_pipeline.checkin2 --fetch-osm
```

Arquivos OSM gerados:

- `experiments/output/checkin2/osm/osm_raw_overpass.json`;
- `experiments/output/checkin2/osm/osm_road_network.geojson`;
- `experiments/output/checkin2/osm/osm_summary.json`.

Para executar as duas fontes geográficas:

```powershell
python -m sergipe_traffic_ai.data_pipeline.checkin2 --fetch-geography --fetch-osm
```

Se a rede estiver indisponível, o pipeline registra a falha sem impedir o restante da demonstração.

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

Se o GeoJSON do OpenStreetMap já tiver sido gerado, o Pygame inicia em **modo OSM**. A tecla **G** alterna entre a rede viária real projetada e a representação esquemática anterior. Os veículos são alinhados aos eixos viários identificados pelo nome das vias do cenário piloto.

## Roteiro de fala curto

> O projeto usa uma estratégia híbrida de dados. O IBGE fornece o contexto territorial e o OpenStreetMap, consultado pela Overpass API, fornece a rede viária do entorno do cenário piloto. Nós pré-processamos as vias para normalizar atributos como sentido, faixas e velocidade máxima. Nesta etapa, porém, a demanda de veículos ainda é sintética e reproduzível por seed; portanto, não afirmamos usar contagens reais de tráfego de Aracaju. Como referência experimental, usamos um controlador de tempo fixo sem IA. Nas etapas seguintes, esse baseline será comparado com controladores adaptativos e com Reinforcement Learning.
