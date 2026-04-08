# EVM Project Manager (Web)

 Aplicacao web que permite configurar squads, planejar releases, registrar sprints e gerar indicadores EVM em tempo real para apoiar decisao tatico-operacional e executiva e com isso, aumentar a previsibilidade de custo e prazo, reduzir leitura subjetiva do status do projeto e dar transparencia para comparacao entre baseline e execucao e apoiar governanca por squad, release e sprint.


 ## Principais features

* autenticacao por usuario
* importacao inicial da estrutura de squads via planilha
* gestao de squad por time e custos
* planejamento de releases com pontos e sprints
* baseline por squad
* registro, edicao e exclusao de sprints
* metricas EVM e projecoes
* dashboards geral e por squad
* exportacao de relatorios executivos em PDF


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

4. Defina uma chave secreta para a sessao:

```powershell
$env:FLASK_SECRET_KEY="troque-por-uma-chave-longa-e-aleatoria"
```

5. Suba a aplicacao:

```powershell
python app.py
```

6. Alternativa mais segura, sem depender da ativacao da virtualenv:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

7. Atalho de inicializacao em PowerShell:

```powershell
.\run.ps1
```

8. Acesse:

```text
http://127.0.0.1:5000
```

## Testes

Para rodar a suite com cobertura:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest --cov --cov-report=term-missing
```

## Documentacao

- Guia de funcionalidades e uso: [GUIA_FUNCIONALIDADES.md](GUIA_FUNCIONALIDADES.md)

## Observacoes

- Cada usuario possui suas squads e workspaces persistidos localmente em SQLite.
- O frontend usa templates parciais para reduzir repeticoes.
- Se aparecer `ModuleNotFoundError`, quase sempre significa que a aplicacao foi executada fora da `.venv`.
- Em producao, use `FLASK_SECRET_KEY` e `FLASK_SESSION_COOKIE_SECURE=1`.
