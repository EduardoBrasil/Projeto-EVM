# Guia do App EVM

## Visao Geral

O app foi construido para apoiar o acompanhamento de squads e projetos com EVM (Earned Value Management), permitindo configurar a composicao da equipe, planejar releases, registrar sprints, acompanhar custo e prazo, e comparar o estado atual com uma baseline.

## Funcionalidades Atuais

### 1. Autenticacao

- Cadastro de usuario
- Login e logout
- Persistencia dos dados por usuario

### 2. Importacao de Squads

- Upload de planilha em `.xlsx`, `.xls` ou `.csv`
- Leitura das squads e seus membros
- Criacao automatica das squads no sistema
- Reset completo dos dados para novo upload

### 3. Selecao e Gestao de Squads

- Tela para selecionar a squad ativa
- Criacao manual de nova squad
- Exclusao de squad
- Navegacao por menu lateral e dashboard

### 4. Configuracao da Squad

- Ajuste de membros importados da planilha
- Inclusao de membros adicionais manualmente
- Edicao de cargo, funcao, salario, valor/hora e quantidade
- Remocao de membros importados e manuais

### 5. Custos Complementares da Squad

- Cadastro por squad de:
  - custo de infraestrutura
  - custo de plano de saude
  - vale alimentacao e refeicao
- Consolidacao automatica desses valores no `Custo da Squad`
- Reflexo automatico no custo por sprint, BAC e projecoes

### 6. Planejamento de Releases

- Criacao de releases
- Definicao de pontos por release
- Definicao de sprints por release
- Bloqueio da estrutura das releases apos a configuracao inicial

### 7. Planejamento da Sprint

- Configuracao da duracao padrao da sprint
- Calculo automatico de:
  - custo da squad
  - custo base da sprint
  - BAC
  - valor por ponto
- Sugestao automatica de `PV` e `AC` com base no custo da sprint

### 8. Registro de Sprint

- Registro de:
  - pontos planejados
  - pontos concluidos
  - pontos adicionados
  - PV
  - AC
  - duracao da sprint
- Recalculo automatico do historico
- Inclusao progressiva dos pontos adicionados no escopo da release

### 9. Edicao e Exclusao de Sprint

- Edicao inline das sprints registradas
- Exclusao de sprint
- Recalculo automatico de metricas e projecoes apos qualquer alteracao

### 10. Metricas EVM

O app calcula e exibe:

- PV
- EV
- AC
- CV
- SV
- CPI
- SPI
- percentual concluido do projeto
- status da sprint e status acumulado do projeto

### 11. Projecoes do Projeto

- Projecao de custo final
- Projecao de prazo final
- Variacao projetada de custo
- Sprints restantes projetadas
- Status executivo do projeto com base em custo e atraso

### 12. Graficos

- Grafico cumulativo de `PV`, `EV` e `AC`
- Grafico de `CPI`
- Grafico de `SPI`
- Secoes recolhiveis/expansiveis
- Legendas interpretativas para leitura dos indicadores

### 13. Dashboard Geral

- Visao resumida de todas as squads
- Status de cada projeto
- BAC
- Custo da Squad
- Conclusao
- Previsao de entrega
- Acesso rapido ao dashboard da squad e ao planejamento

### 14. Dashboard da Squad

- Resumo executivo do projeto
- Ultima medicao
- Historico de sprints
- Acompanhamento do projeto

### 15. Baseline v1

- Geracao de uma baseline por squad
- Aba exclusiva de baseline no menu lateral
- Captura do snapshot atual de:
  - escopo
  - prazo
  - custo da squad
  - custo por sprint
  - BAC
  - valor por ponto
  - custos adicionais
- Comparacao entre baseline e estado atual

## Guia de Uso

## Fluxo Recomendado

1. Fazer login no sistema.
2. Importar a planilha das squads.
3. Selecionar a squad desejada.
4. Revisar a composicao da squad em `Configuracao da Squad`.
5. Ajustar custos complementares da squad.
6. Ir para `Planejamento da Squad`.
7. Configurar releases, pontos e sprints.
8. Gerar a baseline inicial.
9. Registrar as sprints ao longo da execucao.
10. Acompanhar dashboards, metricas, graficos e projecoes.

## Como Configurar a Squad

Na tela `Configuracao da Squad` voce pode:

- revisar os membros vindos da planilha
- alterar quantidades
- adicionar membros manuais
- ajustar custos complementares da squad

O `Custo da Squad` sera recalculado automaticamente com base em:

- custo da planilha
- custo manual
- infraestrutura
- plano de saude
- vale alimentacao e refeicao

## Como Planejar Releases

Na tela `Planejamento da Squad`:

- defina quantas releases deseja planejar
- informe os pontos de cada release
- informe quantas sprints cada release deve consumir

Com isso o sistema calcula:

- total de pontos da release
- total de sprints
- custo base da sprint
- BAC
- estado da baseline

## Como Gerar a Baseline

Depois que o planejamento estiver pronto:

1. clique em `Gerar baseline`
2. o sistema salva a referencia atual da squad
3. a baseline passa a aparecer na aba `Baseline do Projeto`

Quando o plano mudar, voce pode usar `Atualizar baseline`.

## Como Registrar uma Sprint

Preencha:

- pontos planejados
- pontos concluidos
- pontos adicionados
- PV
- AC
- semanas da sprint

Depois de salvar, o sistema:

- atualiza o historico
- recalcula metricas EVM
- atualiza projecoes
- atualiza graficos
- atualiza o dashboard da squad

## Como Ler os Indicadores

- `CPI > 1`: eficiencia de custo melhor que o esperado
- `CPI = 1`: custo aderente ao planejado
- `CPI < 1`: acima do custo esperado
- `SPI > 1`: adiantado
- `SPI = 1`: no ritmo planejado
- `SPI < 1`: atrasado

No grafico cumulativo:

- `EV abaixo de PV`: atraso
- `EV abaixo de AC`: custo acima do esperado

## Como Usar o Dashboard

### Dashboard Geral

Use para comparar rapidamente todas as squads.

### Dashboard da Squad

Use para analisar a squad ativa em mais profundidade:

- status atual
- ultima medicao
- baseline
- historico de sprints
- acompanhamento do projeto

## Observacoes Importantes

- Cada squad possui planejamento isolado.
- Cada usuario possui seus dados persistidos separadamente.
- Pontos adicionados durante as sprints entram no escopo atual da release.
- Alteracoes de custo da squad impactam o planejamento automaticamente.
- A baseline atual e unica por squad nesta versao.

## Proximos Passos Naturais

Se o produto evoluir, os proximos recursos recomendados sao:

- versionamento de baseline
- motivo da mudanca de baseline
- exportacao de relatorios
- alertas visuais de desvio
- historico de auditoria por alteracao
