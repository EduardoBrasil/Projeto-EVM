# EVM Project Manager (Web)

Aplicativo web para acompanhamento de squads com EVM (Earned Value Management), planejamento por release e dashboard por projeto.

## Estrutura

```text
Projeto EVM/
|- app.py
|- routes.py
|- dashboard_routes.py
|- squad_routes.py
|- planning_routes.py
|- chart_routes.py
|- route_helpers.py
|- services.py
|- models.py
|- charts.py
|- templates/
|  |- partials/
|- static/
|- tests/
|- requirements.txt
|- requirements-dev.txt
```

## Execução

1. Crie a virtualenv:

```powershell
python -m venv .venv
```

2. Ative o ambiente:

```powershell
.venv\Scripts\Activate.ps1
```

3. Instale as dependências:

```powershell
pip install -r requirements.txt
```

4. Suba a aplicação:

```powershell
python app.py
```

5. Acesse:

```text
http://127.0.0.1:5000
```

## Testes

Para rodar a suíte com cobertura:

```powershell
pip install -r requirements-dev.txt
pytest --cov --cov-report=term-missing
```

## Observações

- Cada squad possui planejamento isolado.
- O frontend usa templates parciais para reduzir repetição.
- A versão desktop antiga foi removida do repositório.
