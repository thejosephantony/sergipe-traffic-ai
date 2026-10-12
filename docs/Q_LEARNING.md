# Q-Learning — Sergipe Traffic AI

## Objetivo

O Q-Learning é o primeiro controlador do projeto que **aprende uma política a partir da interação com o simulador**.

A comparação experimental prevista passa a ser:

1. tempo fixo — baseline sem IA;
2. adaptativo — heurística programada;
3. Q-Learning — agente treinado.

## Estado

O algoritmo, o ambiente de treinamento, a persistência da Q-table e o controlador de execução estão implementados.

O arquivo treinado **não é pré-fabricado no repositório**. Ele é gerado ao executar o treinamento, evitando apresentar como resultado científico uma política que ainda não foi treinada e avaliada no ambiente do usuário.

## Estado observado pelo agente

O Q-Learning é tabular; por isso, as variáveis são discretizadas.

O estado possui quatro componentes:

```text
(
  categoria_fila_barao,
  categoria_fila_augusto,
  fase_semaforica,
  categoria_tempo_na_fase
)
```

As filas são agrupadas em categorias:

- 0 veículos;
- 1–3;
- 4–7;
- 8–12;
- 13 ou mais.

A fase é codificada como:

- verde Barão/Maynard;
- verde Augusto Franco;
- fase de transição/segurança.

O tempo de verde indica se a fase ainda está bloqueada pelo verde mínimo, se já permite troca ou se está próxima do verde máximo.

## Ações

O agente possui somente duas ações:

```text
0 = manter
1 = solicitar troca
```

A IA **não pode abrir diretamente o verde conflitante**.

Uma máquina determinística de segurança recebe a solicitação e aplica:

```text
VERDE
→ AMARELO
→ TODOS VERMELHOS
→ VERDE CONFLITANTE
```

Também são respeitados os tempos mínimo e máximo de verde configurados no cenário.

**Intertravamento físico:** após o amarelo e o período mínimo de todos-vermelhos,
a máquina mantém ambos os eixos bloqueados enquanto existirem veículos que
já passaram da linha de retenção. Isso vale para o baseline fixo, o adaptativo
e o Q-Learning. O critério atual é conservador: libera só quando esses veículos
saem da área simulada. O cenário piloto usa 4 s de amarelo e 2 s de
todos-vermelhos como valores mínimos iniciais, sujeitos a validação.


## Recompensa

A função inicial de recompensa considera:

```text
reward =
    - peso_fila × fila_total
    - peso_espera × espera_observada
    + peso_throughput × veículos_concluídos
    - penalidade_de_troca
```

Os pesos estão registrados no cenário e devem ser tratados como hiperparâmetros experimentais, não como valores definitivos.

## Atualização da Q-table

A atualização usa a equação clássica:

```text
Q(s,a) ← Q(s,a) + α [r + γ max Q(s',a') - Q(s,a)]
```

Onde:

- `α` é a taxa de aprendizado;
- `γ` é o fator de desconto;
- `ε` controla exploração epsilon-greedy.

Durante o treinamento, `ε` decai progressivamente. Na avaliação e no Pygame, a política é executada com `ε = 0`.

## Treinamento

Na raiz do projeto:

```powershell
python experiments/train_q_learning.py
```

Configuração padrão:

- 200 episódios;
- 600 segundos simulados por episódio;
- seeds consecutivas a partir de 42.

Para um teste rápido:

```powershell
python experiments/train_q_learning.py --episodes 20 --duration 300
```

O treinamento gera:

```text
models/q_learning_aracaju.json
experiments/output/q_learning/training_history.csv
```

O JSON contém a Q-table e metadados do treinamento.

## Avaliação

A política treinada pode ser avaliada sem exploração:

```powershell
python experiments/evaluate_q_learning.py
```

Por padrão, são usadas 20 seeds de avaliação diferentes das seeds iniciais de treinamento.

O script reporta:

- espera média dos veículos concluídos;
- fila média;
- throughput médio;
- reward;
- quantidade de trocas aceitas.

## Pygame

Depois que `models/q_learning_aracaju.json` existir:

```powershell
python -m sergipe_traffic_ai.visual.app
```

Controles:

- `1` — baseline fixo;
- `2` — adaptativo por regras;
- `3` — Q-Learning treinado.

Se a tecla `3` for pressionada sem um modelo treinado, o controlador atual é mantido e uma mensagem é exibida no terminal.

## Validade experimental

Treinar uma Q-table não basta para afirmar que a IA é melhor.

A conclusão deve vir de comparação com os mesmos cenários e seeds entre os controladores. Resultados devem ser reportados com várias execuções, e não a partir de uma única seed favorável.

## Atualização do modelo após esta correção

Mudanças na dinâmica de segurança alteram as trajetórias dos episódios e a
recompensa observada. **Reexecute o treinamento e a avaliação** antes de
apresentar resultados da nova versão. A Q-table antiga ainda pode ser
carregada, mas foi aprendida sob as regras anteriores.

```powershell
python experiments/train_q_learning.py
python experiments/evaluate_q_learning.py
```

Essas restrições são apropriadas para este protótipo simplificado e **não
representam certificação de segurança viária em ambiente real**.
