# EVM Project Manager (Web)

Aplicativo web para acompanhamento de squads com EVM (Earned Value Management), planejamento por release e dashboard por projeto.

## Estrutura

```text
Projeto EVM/
|- app.py
|- auth_routes.py
|- routes.py
|- dashboard_routes.py
|- squad_routes.py
|- planning_routes.py
|- chart_routes.py
|- route_helpers.py
|- services.py
|- storage.py
|- models.py
|- charts.py
|- templates/
|  |- partials/
|- static/
|- tests/
|- requirements.txt
|- requirements-dev.txt
```

## Execucao

1. Crie a virtualenv:

```powershell
python -m venv .venv
```

2. Se estiver no PowerShell, ative o ambiente:

```powershell
.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a ativacao, rode:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.venv\Scripts\Activate.ps1
```

3. Instale as dependencias:

```powershell
python -m pip install -r requirements.txt
```

4. Suba a aplicacao:

```powershell
python app.py
```

5. Alternativa mais segura, sem depender da ativacao da virtualenv:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

6. Atalho de inicializacao em PowerShell:

```powershell
.\run.ps1
```

7. Acesse:

```text
http://127.0.0.1:5000
```

## Testes

Para rodar a suite com cobertura:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest --cov --cov-report=term-missing
```

## Observacoes

- Cada usuario possui suas squads e workspaces persistidos localmente em SQLite.
- O frontend usa templates parciais para reduzir repeticoes.
- Se aparecer `ModuleNotFoundError`, quase sempre significa que a aplicacao foi executada fora da `.venv`.
