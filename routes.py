"""
routes.py - Rotas da aplicação web
"""

import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.utils import secure_filename
from models import Squad, EVMCalculator, SquadLoader
import io
import base64
import copy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Blueprint para rotas
routes_bp = Blueprint('routes', __name__)

# Configuração de upload
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

def allowed_file(filename):
    """Verifica se arquivo tem extensão permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def normalize_releases(releases):
    """Converte releases antigas (floats) para novo formato (dicionários)."""
    if not releases:
        return []
    
    normalized = []
    for r in releases:
        if isinstance(r, dict):
            normalized.append(r)
        else:
            # Release antiga como float, converter para novo formato
            normalized.append({'points': float(r), 'sprints': 5})
    
    return normalized


def parse_brazilian_float(value):
    """Converte formato brasileiro (48.924,5) para decimal (48924.5)."""
    if isinstance(value, (int, float)):
        return float(value)
    
    if not isinstance(value, str):
        return 0.0
    
    value = value.strip()
    
    # Se não tem ponto nem vírgula, é um inteiro
    if '.' not in value and ',' not in value:
        try:
            return float(value)
        except ValueError:
            return 0.0
    
    # Se tem ponto e vírgula, o ponto é separador de milhares, vírgula é decimal
    if '.' in value and ',' in value:
        # 48.924,5 -> 48924.5
        value = value.replace('.', '').replace(',', '.')
        try:
            return float(value)
        except ValueError:
            return 0.0
    
    # Se tem só vírgula, é decimal brasileiro
    if ',' in value:
        value = value.replace(',', '.')
        try:
            return float(value)
        except ValueError:
            return 0.0
    
    # Se tem só ponto, é decimal americano
    if '.' in value:
        try:
            return float(value)
        except ValueError:
            return 0.0
    
    return 0.0


def get_squad_workspaces():
    """Retorna o dicionário de planejamentos por squad."""
    return session.setdefault('squad_workspaces', {})


def get_current_squad_name():
    """Retorna o nome da squad atualmente selecionada."""
    return session.get('current_squad_name')


def ensure_current_squad_workspace():
    """Garante que a squad atual tenha um workspace próprio na sessão."""
    squad_name = get_current_squad_name()
    if not squad_name:
        return None

    squads_data = session.get('squads_data', {})
    squad_info = squads_data.get(squad_name, {})
    base_members = copy.deepcopy(squad_info.get('members', []))
    base_total_cost = squad_info.get('total_cost', 0)

    workspaces = get_squad_workspaces()
    if squad_name not in workspaces:
        workspaces[squad_name] = {
            'members': [],
            'releases': [],
            'history': [],
            'squad_members_from_file': base_members,
            'squad_total_cost': base_total_cost,
        }
        session['squad_workspaces'] = workspaces
        session.modified = True

    workspace = workspaces[squad_name]
    workspace.setdefault('members', [])
    workspace.setdefault('releases', [])
    workspace.setdefault('history', [])
    workspace.setdefault('squad_members_from_file', copy.deepcopy(base_members))
    workspace.setdefault('squad_total_cost', base_total_cost)
    return workspace


def save_current_squad_workspace(workspace):
    """Persiste o workspace da squad atual na sessão."""
    squad_name = get_current_squad_name()
    if not squad_name:
        return
    workspaces = get_squad_workspaces()
    workspaces[squad_name] = workspace
    session['squad_workspaces'] = workspaces
    session.modified = True


def get_or_create_workspace_for_squad(squad_name):
    """Retorna o workspace de uma squad específica sem depender da navegação atual."""
    current_squad = get_current_squad_name()
    session['current_squad_name'] = squad_name
    workspace = ensure_current_squad_workspace()
    session['current_squad_name'] = current_squad
    session.modified = True
    return workspace


def calculate_workspace_summary(squad_name, workspace, squad_info):
    """Monta um resumo executivo da squad para o dashboard."""
    base_total_cost = squad_info.get('total_cost', 0)
    file_members = workspace.get('squad_members_from_file', squad_info.get('members', []))
    members = workspace.get('members', [])
    manual_cost = sum(m.get('salary', 0) + 160 * m.get('hourly', 0) for m in members)
    squad_cost = workspace.get('squad_cost', base_total_cost + manual_cost)
    releases = normalize_releases(workspace.get('releases', []))
    total_points = sum(r.get('points', 0) for r in releases)
    total_sprints = sum(r.get('sprints', 0) for r in releases)
    sprint_cost = squad_cost / 2 if squad_cost > 0 else 0
    bac = sprint_cost * total_sprints
    value_per_point = bac / total_points if total_points > 0 else 0
    history = recalculate_history(workspace.get('history', []), value_per_point, total_points)
    last_metrics = history[-1] if history else None
    projection = calculate_release_projection(history, bac, total_sprints)

    return {
        'name': squad_name,
        'members_from_file': len(file_members),
        'manual_members': len(members),
        'squad_cost': squad_cost,
        'sprint_cost': sprint_cost,
        'releases_count': len(releases),
        'total_points': total_points,
        'total_sprints': total_sprints,
        'history_count': len(history),
        'bac': bac,
        'completion_percentage': last_metrics.get('completion_percentage', 0) if last_metrics else 0,
        'status': last_metrics.get('status', 'Não iniciado') if last_metrics else 'Não iniciado',
        'last_metrics': last_metrics,
        'projection': projection,
    }


def get_workspace_planning_context(workspace):
    """Calcula contexto consolidado do planejamento da squad."""
    releases = normalize_releases(workspace.get('releases', []))
    squad_cost = workspace.get('squad_cost', 0)
    total_points = sum(r.get('points', 0) for r in releases)
    total_sprints = sum(r.get('sprints', 0) for r in releases)
    sprint_cost = squad_cost / 2 if squad_cost > 0 else 0
    bac = sprint_cost * total_sprints
    value_per_point = bac / total_points if total_points > 0 else 0
    history = recalculate_history(workspace.get('history', []), value_per_point, total_points)
    return {
        'releases': releases,
        'squad_cost': squad_cost,
        'total_points': total_points,
        'total_sprints': total_sprints,
        'sprint_cost': sprint_cost,
        'bac': bac,
        'value_per_point': value_per_point,
        'history': history,
    }


def build_sprint_record(
    sprint_number,
    planned_points,
    earned_points,
    added_points,
    actual_cost,
    value_per_point,
    cumulative_done_points,
    total_release_points,
    planned_value=None,
):
    """Monta um registro de sprint com métricas EVM consistentes."""
    if planned_value is not None:
        completion_ratio = (earned_points / planned_points) if planned_points > 0 else 0
        ev = planned_value * completion_ratio
        pv = planned_value
        cv = ev - actual_cost
        sv = ev - pv
        cpi = ev / actual_cost if actual_cost > 0 else 0
        spi = ev / pv if pv > 0 else 0
        status = EVMCalculator.get_status(cpi, spi)
        metrics = {
            'PV': pv,
            'EV': ev,
            'AC': actual_cost,
            'CV': cv,
            'SV': sv,
            'CPI': cpi,
            'SPI': spi,
            'status': status,
        }
    else:
        metrics = EVMCalculator.calculate_sprint_metrics(
            planned_points=planned_points,
            earned_points=earned_points,
            actual_cost=actual_cost,
            value_per_point=value_per_point,
        )

    completion_percentage = (
        (cumulative_done_points / total_release_points) * 100 if total_release_points > 0 else 0
    )

    return {
        'sprint_no': sprint_number,
        'plan_points': planned_points,
        'done_points': earned_points,
        'added_points': added_points,
        'PV': metrics['PV'],
        'EV': metrics['EV'],
        'AC': metrics['AC'],
        'CV': metrics['CV'],
        'SV': metrics['SV'],
        'CPI': round(metrics['CPI'], 2),
        'SPI': round(metrics['SPI'], 2),
        'status': metrics['status'],
        'completion_percentage': round(completion_percentage, 2),
    }


def recalculate_history(history, value_per_point, total_release_points):
    """Recalcula o histórico salvo na sessão usando as fórmulas corretas."""
    recalculated_history = []
    cumulative_done_points = 0.0

    for index, record in enumerate(history, start=1):
        planned_points = float(record.get('plan_points', 0) or 0)
        done_points = float(record.get('done_points', 0) or 0)
        added_points = float(record.get('added_points', 0) or 0)
        actual_cost = parse_brazilian_float(record.get('AC', 0))
        planned_value = (
            parse_brazilian_float(record.get('PV', 0))
            if record.get('PV') is not None
            else None
        )

        cumulative_done_points += done_points
        recalculated_history.append(
            build_sprint_record(
                sprint_number=index,
                planned_points=planned_points,
                earned_points=done_points,
                added_points=added_points,
                actual_cost=actual_cost,
                value_per_point=value_per_point,
                cumulative_done_points=cumulative_done_points,
                total_release_points=total_release_points,
                planned_value=planned_value,
            )
        )

    return recalculated_history


def calculate_release_projection(history, bac, total_sprints):
    """Calcula projeção de custo e prazo até o fim da release."""
    if not history:
        return {
            'cpi': 0,
            'spi': 0,
            'eac': bac,
            'cost_variance_at_completion': 0,
            'projected_total_sprints': total_sprints,
            'delay_sprints': 0,
            'projected_remaining_sprints': total_sprints,
        }

    cumulative_ac = sum(record.get('AC', 0) for record in history)
    cumulative_ev = sum(record.get('EV', 0) for record in history)
    cumulative_pv = sum(record.get('PV', 0) for record in history)

    cpi = (cumulative_ev / cumulative_ac) if cumulative_ac > 0 else 0
    spi = (cumulative_ev / cumulative_pv) if cumulative_pv > 0 else 0

    eac = (bac / cpi) if cpi > 0 else 0
    projected_total_sprints = (total_sprints / spi) if spi > 0 else 0
    delay_sprints = projected_total_sprints - total_sprints if projected_total_sprints > 0 else 0
    remaining_sprints = max(total_sprints - len(history), 0)
    projected_remaining_sprints = (
        max(projected_total_sprints - len(history), 0) if projected_total_sprints > 0 else 0
    )

    return {
        'cpi': round(cpi, 2),
        'spi': round(spi, 2),
        'eac': round(eac, 2),
        'cost_variance_at_completion': round(eac - bac, 2),
        'projected_total_sprints': round(projected_total_sprints, 2),
        'delay_sprints': round(delay_sprints, 2),
        'planned_remaining_sprints': remaining_sprints,
        'projected_remaining_sprints': round(projected_remaining_sprints, 2),
    }


def _get_planning_totals(workspace):
    """Retorna totais consolidados do planejamento atual."""
    releases = normalize_releases(workspace.get('releases', []))
    squad_cost = workspace.get('squad_cost', 0)
    total_release_points = sum(r.get('points', 0) for r in releases)
    total_release_sprints = sum(r.get('sprints', 0) for r in releases)
    sprint_cost = squad_cost / 2 if squad_cost > 0 else 0
    bac = sprint_cost * total_release_sprints
    value_per_point = bac / total_release_points if total_release_points > 0 else 0
    return {
        'releases': releases,
        'total_release_points': total_release_points,
        'total_release_sprints': total_release_sprints,
        'value_per_point': value_per_point,
    }


@routes_bp.route('/', methods=['GET'])
def index():
    """Redireciona para o dashboard inicial ou upload."""
    if 'squads_data' in session and session['squads_data']:
        return redirect(url_for('routes.dashboard'))
    return redirect(url_for('routes.upload_file'))


@routes_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """Página inicial com resumo de todas as squads."""
    squads_data = session.get('squads_data', {})
    if not squads_data:
        return redirect(url_for('routes.upload_file'))

    current_squad = get_current_squad_name()
    summaries = []

    if current_squad is None:
        current_squad = next(iter(squads_data.keys()), None)
        if current_squad is not None:
            session['current_squad_name'] = current_squad
            session.modified = True

    for squad_name, squad_info in squads_data.items():
        workspace = get_or_create_workspace_for_squad(squad_name)
        summaries.append(calculate_workspace_summary(squad_name, workspace, squad_info))

    current_summary = next((item for item in summaries if item['name'] == current_squad), None)

    return render_template(
        'dashboard.html',
        summaries=summaries,
        current_squad=current_squad,
        current_summary=current_summary,
    )


@routes_bp.route('/dashboard/squad/<squad_name>', methods=['GET'])
def squad_dashboard(squad_name):
    """Dashboard detalhado de uma squad específica."""
    squads_data = session.get('squads_data', {})
    if squad_name not in squads_data:
        flash('Squad inválida.', 'error')
        return redirect(url_for('routes.dashboard'))

    session['current_squad_name'] = squad_name
    workspace = get_or_create_workspace_for_squad(squad_name)
    session.modified = True

    current_summary = calculate_workspace_summary(squad_name, workspace, squads_data[squad_name])
    return render_template(
        'squad_dashboard.html',
        current_squad=squad_name,
        current_summary=current_summary,
    )


@routes_bp.route('/switch_squad/<squad_name>', methods=['GET'])
def switch_squad(squad_name):
    """Troca a squad ativa para navegação lateral e páginas de trabalho."""
    squads_data = session.get('squads_data', {})
    if squad_name not in squads_data:
        flash('Squad inválida.', 'error')
        return redirect(url_for('routes.dashboard'))

    session['current_squad_name'] = squad_name
    ensure_current_squad_workspace()
    session.modified = True

    next_page = request.args.get('next', 'routes.dashboard')
    try:
        return redirect(url_for(next_page))
    except Exception:
        return redirect(url_for('routes.dashboard'))


@routes_bp.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """
    Página de upload de arquivo de squads.
    - GET: Exibe formulário de upload
    - POST: Processa arquivo enviado
    """
    if request.method == 'POST':
        # Verificar se arquivo foi enviado
        if 'file' not in request.files:
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('Arquivo vazio', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            try:
                # Carregar dados do arquivo
                squads_data = SquadLoader.load_file(filepath)
                session['squads_data'] = squads_data
                session['squads_list'] = list(squads_data.keys())
                session.pop('squad_workspaces', None)
                session.pop('current_squad_name', None)
                session.modified = True
                
                flash(f'Arquivo carregado com sucesso! {len(squads_data)} squads encontradas.', 'success')
                return redirect(url_for('routes.select_squad'))
            except Exception as e:
                flash(f'Erro ao processar arquivo: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Formato de arquivo não permitido. Use Excel (.xlsx) ou CSV.', 'error')

    return render_template('upload.html')


@routes_bp.route('/select_squad', methods=['GET', 'POST'])
def select_squad():
    """
    Página de seleção de squad.
    - GET: Exibe dropdown com squads disponíveis
    - POST: Processa seleção e carrega dados da squad
    """
    squads_data = session.get('squads_data', {})
    squads_list = list(squads_data.keys())

    if not squads_list:
        flash('Nenhuma squad carregada. Faça upload de arquivo.', 'warning')
        return redirect(url_for('routes.upload_file'))

    if request.method == 'POST':
        selected_squad = request.form.get('selected_squad')

        if selected_squad not in squads_data:
            flash('Squad inválida', 'error')
            return redirect(request.url)

        # Carregar dados da squad para setup
        session['current_squad_name'] = selected_squad
        session.modified = True
        ensure_current_squad_workspace()

        return redirect(url_for('routes.setup'))

    return render_template('select_squad.html', squads=squads_data)


@routes_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """
    Página de configuração da squad.
    - GET: Exibe o formulário com os membros carregados e adicionados
    - POST: Adiciona um novo membro manualmente
    """
    workspace = ensure_current_squad_workspace()
    if workspace is None:
        return redirect(url_for('routes.select_squad'))

    current_squad = session.get('current_squad_name', 'Squad desconhecida')
    members_from_file = workspace.get('squad_members_from_file', [])
    total_file_cost = workspace.get('squad_total_cost', 0)

    if request.method == 'POST':
        role = request.form.get('role', '').strip()
        function = request.form.get('function', '').strip()
        
        try:
            salary = float(request.form.get('salary', 0) or 0)
            hourly = float(request.form.get('hourly', 0) or 0)
        except ValueError:
            salary = 0
            hourly = 0

        if role and function and salary >= 0 and hourly >= 0:
            members = workspace.get('members', [])
            members.append({
                'role': role,
                'function': function,
                'salary': salary,
                'hourly': hourly,
                'source': 'manual',
            })
            workspace['members'] = members
            save_current_squad_workspace(workspace)

    members = workspace.get('members', [])
    
    # Calcular custo de membros adicionados manualmente
    manual_cost = sum(m['salary'] + 160 * m['hourly'] for m in members)
    
    # Custo total = arquivo + manual
    squad_cost = total_file_cost + manual_cost
    workspace['squad_cost'] = squad_cost
    save_current_squad_workspace(workspace)

    return render_template(
        'setup.html',
        current_squad=current_squad,
        members=members,
        members_from_file=members_from_file,
        squad_cost=squad_cost,
        file_cost=total_file_cost,
        manual_cost=manual_cost,
    )


@routes_bp.route('/plan', methods=['GET', 'POST'])
def plan():
    """
    Página de planejamento de releases e sprints.
    - GET: Exibe planejamento e histórico
    - POST: Gerencia releases
    """
    # Verificar se squad foi configurada
    workspace = ensure_current_squad_workspace()
    if workspace is None:
        return redirect(url_for('routes.select_squad'))

    if workspace.get('squad_cost', 0) <= 0:
        return redirect(url_for('routes.setup'))

    # Inicializar releases se não existir
    if 'releases' not in workspace:
        workspace['releases'] = []

    # Normalizar releases (converter antigas para novo formato)
    releases_raw = normalize_releases(workspace.get('releases', []))
    workspace['releases'] = releases_raw

    # Inicializar histórico
    if 'history' not in workspace:
        workspace['history'] = []

    # Processar criação de releases
    if request.method == 'POST' and 'create_releases' in request.form:
        num_releases = int(request.form.get('num_releases', 1))
        # Criar releases com pontos padrão de 50 pontos e 5 sprints cada
        workspace['releases'] = [
            {'points': 50, 'sprints': 5} for _ in range(num_releases)
        ]

    squad_cost = workspace.get('squad_cost', 0)
    current_squad = session.get('current_squad_name', 'Squad')
    releases = list(enumerate(workspace.get('releases', []), 1))  # (número, dicionário)
    total_points = sum(r[1]['points'] for r in releases) if releases else 0
    total_sprints = sum(r[1]['sprints'] for r in releases) if releases else 0

    sprint_cost = squad_cost / 2 if squad_cost > 0 else 0
    bac = sprint_cost * total_sprints
    value_per_point = bac / total_points if total_points > 0 else 0

    history = recalculate_history(workspace.get('history', []), value_per_point, total_points)
    workspace['history'] = history
    save_current_squad_workspace(workspace)
    current_sprint = len(history) + 1
    last_metrics = history[-1] if history else {
        'PV': 0,
        'EV': 0,
        'AC': 0,
        'CV': 0,
        'SV': 0,
        'CPI': 0,
        'SPI': 0,
        'sprint_no': 0,
        'status': '-',
        'completion_percentage': 0,
    }
    projection = calculate_release_projection(history, bac, total_sprints)

    return render_template(
        'plan.html',
        current_squad=current_squad,
        squad_cost=squad_cost,
        sprint_cost=sprint_cost,
        value_per_point=value_per_point,
        bac=bac,
        releases=releases,
        total_points=total_points,
        total_sprints=total_sprints,
        current_sprint=current_sprint,
        history=history,
        last_metrics=last_metrics,
        projection=projection,
    )


@routes_bp.route('/update_release_points', methods=['POST'])
def update_release_points():
    """Atualiza os pontos de uma release."""
    workspace = ensure_current_squad_workspace()
    if workspace is None:
        return redirect(url_for('routes.select_squad'))
    releases = normalize_releases(workspace.get('releases', []))
    release_index = int(request.form.get('release_index', 0))
    new_points = float(request.form.get('release_points', 50))
    
    if 0 <= release_index < len(releases):
        releases[release_index]['points'] = new_points
        workspace['releases'] = releases
        save_current_squad_workspace(workspace)
        flash(f"Release {release_index + 1} atualizada para {new_points} pontos.", 'success')
    else:
        flash('Índice de release inválido.', 'error')
    
    return redirect(url_for('routes.plan'))


@routes_bp.route('/update_release_sprints', methods=['POST'])
def update_release_sprints():
    """Atualiza o número de sprints de uma release."""
    workspace = ensure_current_squad_workspace()
    if workspace is None:
        return redirect(url_for('routes.select_squad'))
    releases = normalize_releases(workspace.get('releases', []))
    release_index = int(request.form.get('release_index', 0))
    new_sprints = int(request.form.get('release_sprints', 5))
    
    if 0 <= release_index < len(releases):
        releases[release_index]['sprints'] = new_sprints
        workspace['releases'] = releases
        save_current_squad_workspace(workspace)
        flash(f"Release {release_index + 1} atualizada para {new_sprints} sprints.", 'success')
    else:
        flash('Índice de release inválido.', 'error')
    
    return redirect(url_for('routes.plan'))


@routes_bp.route('/add_release', methods=['POST'])
def add_release():
    """Adiciona uma nova release."""
    workspace = ensure_current_squad_workspace()
    if workspace is None:
        return redirect(url_for('routes.select_squad'))
    releases = normalize_releases(workspace.get('releases', []))
    new_release_points = float(request.form.get('new_release_points', 50))
    new_release_sprints = int(request.form.get('new_release_sprints', 5))
    
    releases.append({
        'points': new_release_points,
        'sprints': new_release_sprints
    })
    workspace['releases'] = releases
    save_current_squad_workspace(workspace)
    flash(f"Nova release adicionada com {new_release_points} pontos e {new_release_sprints} sprints.", 'success')
    
    return redirect(url_for('routes.plan'))


@routes_bp.route('/delete_release', methods=['POST'])
def delete_release():
    """Remove uma release."""
    workspace = ensure_current_squad_workspace()
    if workspace is None:
        return redirect(url_for('routes.select_squad'))
    releases = normalize_releases(workspace.get('releases', []))
    release_index = int(request.form.get('release_index', 0))
    
    if 0 <= release_index < len(releases):
        removed = releases.pop(release_index)
        workspace['releases'] = releases
        save_current_squad_workspace(workspace)
        flash(f"Release removida ({removed['points']} pontos, {removed['sprints']} sprints).", 'success')
    else:
        flash('Índice de release inválido.', 'error')
    
    return redirect(url_for('routes.plan'))


@routes_bp.route('/add_sprint', methods=['POST'])
def add_sprint():
    """
    Adiciona uma novo registro de sprint ao histórico.
    Calcula todas as métricas de EVM baseado nos valores inseridos.
    """
    # Verificar se squad foi configurada
    workspace = ensure_current_squad_workspace()
    if workspace is None:
        return redirect(url_for('routes.select_squad'))

    if workspace.get('squad_cost', 0) <= 0:
        return redirect(url_for('routes.setup'))

    planning_totals = _get_planning_totals(workspace)
    releases = planning_totals['releases']
    
    # Se não houver releases definidas, redirecionar para criar
    if not releases:
        flash('Por favor, configure as releases primeiro.', 'warning')
        return redirect(url_for('routes.plan'))

    total_release_points = planning_totals['total_release_points']
    value_per_point = planning_totals['value_per_point']

    # Obter dados do formulário
    try:
        sprint_plan_points = float(request.form.get('sprint_plan_points', 0))
        sprint_done_points = float(request.form.get('sprint_done_points', 0))
        sprint_added_points = float(request.form.get('sprint_added_points', 0))
        sprint_planned_value = parse_brazilian_float(request.form.get('sprint_planned_value', 0))
        sprint_actual_cost = parse_brazilian_float(request.form.get('sprint_actual_cost', 0))
    except (ValueError, TypeError):
        flash('Erro ao processar os valores inseridos.', 'error')
        return redirect(url_for('routes.plan'))

    # Adicionar ao histórico usando as fórmulas padrão do projeto
    history = recalculate_history(workspace.get('history', []), value_per_point, total_release_points)
    sprint_number = len(history) + 1
    total_done_points = sum(h.get('done_points', 0) for h in history) + sprint_done_points

    record = build_sprint_record(
        sprint_number=sprint_number,
        planned_points=sprint_plan_points,
        earned_points=sprint_done_points,
        added_points=sprint_added_points,
        actual_cost=sprint_actual_cost,
        value_per_point=value_per_point,
        cumulative_done_points=total_done_points,
        total_release_points=total_release_points,
        planned_value=sprint_planned_value,
    )

    history.append(record)
    workspace['history'] = history
    save_current_squad_workspace(workspace)
    
    flash(f'Sprint {sprint_number} registrada com sucesso!', 'success')

    return redirect(url_for('routes.plan'))


@routes_bp.route('/update_sprint/<int:sprint_no>', methods=['POST'])
def update_sprint(sprint_no):
    """Atualiza um registro existente da sprint e recalcula o histórico."""
    workspace = ensure_current_squad_workspace()
    if workspace is None:
        return redirect(url_for('routes.select_squad'))

    planning_totals = _get_planning_totals(workspace)
    if not planning_totals['releases']:
        flash('Por favor, configure as releases antes de editar a sprint.', 'warning')
        return redirect(url_for('routes.plan'))

    history = list(workspace.get('history', []))
    sprint_index = sprint_no - 1
    if sprint_index < 0 or sprint_index >= len(history):
        flash('Sprint não encontrada para edição.', 'error')
        return redirect(url_for('routes.plan'))

    try:
        history[sprint_index]['plan_points'] = float(request.form.get('sprint_plan_points', 0))
        history[sprint_index]['done_points'] = float(request.form.get('sprint_done_points', 0))
        history[sprint_index]['added_points'] = float(request.form.get('sprint_added_points', 0))
        history[sprint_index]['PV'] = parse_brazilian_float(request.form.get('sprint_planned_value', 0))
        history[sprint_index]['AC'] = parse_brazilian_float(request.form.get('sprint_actual_cost', 0))
    except (ValueError, TypeError):
        flash('Erro ao processar os dados da sprint.', 'error')
        return redirect(url_for('routes.plan'))

    workspace['history'] = recalculate_history(
        history,
        planning_totals['value_per_point'],
        planning_totals['total_release_points'],
    )
    save_current_squad_workspace(workspace)
    flash(f'Sprint {sprint_no} atualizada com sucesso!', 'success')
    return redirect(url_for('routes.plan'))


@routes_bp.route('/delete_sprint/<int:sprint_no>', methods=['POST'])
def delete_sprint(sprint_no):
    """Exclui uma sprint do histórico atual da squad."""
    workspace = ensure_current_squad_workspace()
    if workspace is None:
        return redirect(url_for('routes.select_squad'))

    planning_totals = _get_planning_totals(workspace)
    history = list(workspace.get('history', []))
    sprint_index = sprint_no - 1
    if sprint_index < 0 or sprint_index >= len(history):
        flash('Sprint não encontrada para exclusão.', 'error')
        return redirect(url_for('routes.plan'))

    history.pop(sprint_index)
    workspace['history'] = recalculate_history(
        history,
        planning_totals['value_per_point'],
        planning_totals['total_release_points'],
    )
    save_current_squad_workspace(workspace)
    flash(f'Sprint {sprint_no} excluída com sucesso!', 'success')
    return redirect(url_for('routes.plan'))


@routes_bp.route('/generate_chart')
def generate_chart():
    """Mantido por compatibilidade; gera o gráfico acumulado principal."""
    return generate_cumulative_chart()


def _build_chart_response(fig):
    """Converte a figura do matplotlib em resposta HTTP PNG."""
    img = io.BytesIO()
    fig.tight_layout()
    fig.savefig(img, format='png', dpi=100, bbox_inches='tight')
    img.seek(0)
    plt.close(fig)
    response = send_file(img, mimetype='image/png')
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response


def _build_empty_chart_response(message='Sem dados para exibir'):
    """Retorna um PNG válido mesmo quando não há histórico."""
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=14, color='#7f8c8d')
    ax.axis('off')
    return _build_chart_response(fig)


@routes_bp.route('/generate_cumulative_chart')
def generate_cumulative_chart():
    """Gera um gráfico cumulativo com PV, EV e AC de todas as sprints."""
    workspace = ensure_current_squad_workspace()
    planning = get_workspace_planning_context(workspace) if workspace else {}
    history = planning.get('history', [])
    
    if not history:
        return _build_empty_chart_response()
    
    sprints = [str(record['sprint_no']) for record in history]
    pv_values = [record['PV'] for record in history]
    ac_values = [record['AC'] for record in history]
    ev_values = [record['EV'] for record in history]
    
    pv_cumulative = []
    ac_cumulative = []
    ev_cumulative = []
    cumsum_pv = 0
    cumsum_ac = 0
    cumsum_ev = 0
    
    for pv, ac, ev in zip(pv_values, ac_values, ev_values):
        cumsum_pv += pv
        cumsum_ac += ac
        cumsum_ev += ev
        pv_cumulative.append(cumsum_pv)
        ac_cumulative.append(cumsum_ac)
        ev_cumulative.append(cumsum_ev)
    
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(sprints, ac_cumulative, marker='o', label='AC Cumulativo', linewidth=2.4, color='#e74c3c', zorder=2)
    ax.plot(sprints, ev_cumulative, marker='s', label='EV Cumulativo', linewidth=2.4, color='#27ae60', zorder=3)
    ax.plot(sprints, pv_cumulative, marker='D', label='PV Cumulativo', linewidth=3.2, color='#f39c12', linestyle='-.', zorder=4)
    ax.scatter(sprints, pv_cumulative, color='#f39c12', edgecolors='white', linewidths=1.1, s=70, zorder=5)
    ax.set_xlabel('Sprint', fontsize=12, fontweight='bold')
    ax.set_ylabel('Valor (R$)', fontsize=12, fontweight='bold')
    ax.set_title('Gráfico Cumulativo - PV, EV e AC', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'R$ {x:,.0f}'))
    return _build_chart_response(fig)


@routes_bp.route('/generate_cpi_chart')
def generate_cpi_chart():
    """Gera um gráfico exclusivo do CPI."""
    workspace = ensure_current_squad_workspace()
    planning = get_workspace_planning_context(workspace) if workspace else {}
    history = planning.get('history', [])

    if not history:
        return _build_empty_chart_response()

    sprints = [str(record['sprint_no']) for record in history]
    cpi_values = [record['CPI'] for record in history]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(sprints, cpi_values, marker='^', linewidth=2, color='#3498db', label='CPI')
    ax.axhline(1, color='#7f8c8d', linestyle='--', linewidth=1, label='Referência = 1')
    ax.set_xlabel('Sprint', fontsize=12, fontweight='bold')
    ax.set_ylabel('CPI', fontsize=12, fontweight='bold')
    ax.set_title('Gráfico de CPI - Cost Performance Index', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    return _build_chart_response(fig)


@routes_bp.route('/generate_spi_chart')
def generate_spi_chart():
    """Gera um gráfico exclusivo do SPI."""
    workspace = ensure_current_squad_workspace()
    planning = get_workspace_planning_context(workspace) if workspace else {}
    history = planning.get('history', [])

    if not history:
        return _build_empty_chart_response()

    sprints = [str(record['sprint_no']) for record in history]
    spi_values = [record['SPI'] for record in history]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(sprints, spi_values, marker='v', linewidth=2, color='#8e44ad', label='SPI')
    ax.axhline(1, color='#7f8c8d', linestyle='--', linewidth=1, label='Referência = 1')
    ax.set_xlabel('Sprint', fontsize=12, fontweight='bold')
    ax.set_ylabel('SPI', fontsize=12, fontweight='bold')
    ax.set_title('Gráfico de SPI - Schedule Performance Index', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    return _build_chart_response(fig)


@routes_bp.route('/remove_member/<int:member_index>', methods=['POST'])
def remove_member(member_index):
    """
    Remove um membro adicionado manualmente da squad.
    """
    workspace = ensure_current_squad_workspace()
    if workspace is None:
        return redirect(url_for('routes.select_squad'))
    members = workspace.get('members', [])
    
    if 0 <= member_index < len(members):
        removed = members.pop(member_index)
        workspace['members'] = members
        save_current_squad_workspace(workspace)
        flash(f"Membro '{removed['role']}' removido com sucesso.", 'success')
    else:
        flash('Índice de membro inválido.', 'error')
    
    return redirect(url_for('routes.setup'))


@routes_bp.route('/remove_file_member/<int:member_index>', methods=['POST'])
def remove_file_member(member_index):
    """
    Remove um membro carregado da planilha da squad.
    """
    workspace = ensure_current_squad_workspace()
    if workspace is None:
        return redirect(url_for('routes.select_squad'))
    file_members = workspace.get('squad_members_from_file', [])
    
    if 0 <= member_index < len(file_members):
        removed = file_members.pop(member_index)
        workspace['squad_members_from_file'] = file_members
        # Recalcular o custo total da planilha
        workspace['squad_total_cost'] = sum(member['total_grupo'] for member in file_members)
        save_current_squad_workspace(workspace)
        flash(f"Membro '{removed['cargo']}' removido com sucesso.", 'success')
    else:
        flash('Índice de membro inválido.', 'error')
    
    return redirect(url_for('routes.setup'))


@routes_bp.route('/reset', methods=['GET'])
def reset():
    """Limpa session e retorna ao upload."""
    session.clear()
    flash('Sessão resetada. Carregue um novo arquivo.', 'success')
    return redirect(url_for('routes.upload_file'))

