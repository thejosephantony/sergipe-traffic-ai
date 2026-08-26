# Especificação inicial do projeto

## Problema

Ciclos semafóricos rígidos podem responder mal a fluxos de tráfego variáveis. O projeto investiga se estratégias adaptativas e de aprendizagem conseguem reduzir filas e tempo de espera em um ambiente virtual controlado.

## Pergunta de pesquisa

**Um controlador semafórico baseado em IA consegue melhorar métricas de mobilidade em relação a um controlador de tempo fixo em cenários simulados inspirados em Sergipe?**

## Hipótese

Controladores que observam o estado do trânsito e ajustam suas decisões dinamicamente podem superar um baseline fixo principalmente em cenários com demanda desigual ou variável.

## Módulos

- motor de simulação;
- modelo de vias e veículos;
- sistema semafórico;
- controladores;
- métricas e experimentos;
- visualização/dashboard;
- ambiente de Reinforcement Learning;
- camada de IA generativa para explicabilidade.

## Princípio experimental

O mesmo cenário deve ser executado com seeds e parâmetros equivalentes para cada controlador. A comparação deve ser quantitativa e repetida em múltiplos episódios.

## Limitações

O ambiente representa uma abstração acadêmica. Resultados de simulação não equivalem a validação em campo.
