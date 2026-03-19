# EVM Project Manager (Web)

Aplicativo web para cálculo de EVM (Earned Value Management) em sprints de um squad.

## Requisitos
- Python 3.11+
- Flask
- Matplotlib
- NumPy

## Estrutura do Projeto

```
Projeto EVM/
├── app.py              # Entry point (configuração Flask)
├── models.py           # Lógica de negócio (Squad, TeamMember, EVMCalculator)
├── routes.py           # Rotas e controllers
├── requirements.txt    # Dependências
├── README.md           # Este arquivo
├── templates/          # Templates HTML
│   ├── base.html       # Layout base
│   ├── setup.html      # Configuração de squad
│   └── plan.html       # Planejamento e registro de sprints
├── static/             # Assets estáticos
│   └── css/
│       └── style.css   # Estilos CSS personalizados
└── .github/
    └── copilot-instructions.md
```

## Instalação

1. Criar ambiente virtual:
   ```bash
   python -m venv .venv
   ```

2. Ativar ambiente virtual:
   ```bash
   .venv\Scripts\Activate.ps1
   ```

3. Instalar dependências:
   ```bash
   pip install -r requirements.txt
   ```

## Uso

Executar a aplicação:
```bash
python app.py
```

Acesse no navegador:
```
http://127.0.0.1:5000/setup
```

## Fluxo da Aplicação

### Etapa 1: Configuração de Squad (pré-condição)
- Adicione membros com cargo, função, salário base, valor/hora
- O app calcula o custo total da squad automaticamente
- Tabela exibe todos os membros
- Necessário configurar pelo menos 1 membro para avançar

### Etapa 2: Planejamento de Sprints
- Predefina pontos por release, pontos por sprint, total de sprints
- BAC é calculado automaticamente (custo squad ÷ pontos release)
- Sprint vigente é rastreada automaticamente

### Etapa 3: Registro de Sprints
- Informe para cada sprint:
  - Pontos planejados
  - Pontos concluídos
  - Pontos adicionados (scope)
  - Custo real (AC)
- Cálculo instantâneo de:
  - **PV** (Planned Value)
  - **EV** (Earned Value)
  - **AC** (Actual Cost)
  - **CV** (Cost Variance)
  - **SV** (Schedule Variance)
  - **CPI** (Cost Performance Index)
  - **SPI** (Schedule Performance Index)
  - **Status** (OK ou Atenção)

### Visualização de Resultados
- Métricas da última sprint em cards
- Histórico completo em tabela
- Status visual com cores (verde = OK, amarelo = atenção)

## Observações Técnicas

- **Arquitetura profissional**: Separação clara de responsabilidades (models, routes, templates)
- **Validação**: Números negativos não são aceitos
- **Session-based**: Dados persistem durante a sessão (alterar para DB em produção)
- **UX amigável**: Interface responsiva com Bootstrap 5
- **Cálculos automáticos**: Todas as métricas EVM são calculadas em tempo real

## Próximas Melhorias (Opcional)

- [ ] Persistência em banco de dados (SQLite/PostgreSQL)
- [ ] Gráficos cumulativos (matplotlib)
- [ ] Exportação de relatórios (PDF/Excel)
- [ ] Autenticação e múltiplos usuários
- [ ] Edição/remoção de membros
- [ ] Edição/remoção de sprints registradas
- [ ] Dashboard com indicadores KPI

## Autor
GitHub Copilot (2026)
