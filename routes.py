"""
routes.py - Rotas da aplicação web
"""

import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.utils import secure_filename
from models import Squad, EVMCalculator, SquadLoader
import io
import base64
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


@routes_bp.route('/', methods=['GET'])
def index():
    """Redireciona para upload de archivos ou setup."""
    if 'squads_data' in session and session['squads_data']:
        return redirect(url_for('routes.select_squad'))
    return redirect(url_for('routes.upload_file'))


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
        squad_info = squads_data[selected_squad]
        session['current_squad_name'] = selected_squad
        session['squad_members_from_file'] = squad_info['members']
        session['squad_total_cost'] = squad_info['total_cost']
        session['members'] = []  # Limpar membros manuais
        session.modified = True

        return redirect(url_for('routes.setup'))

    return render_template('select_squad.html', squads=squads_data)


@routes_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """
    Página de configuração da squad.
    - GET: Exibe o formulário com os membros carregados e adicionados
    - POST: Adiciona um novo membro manualmente
    """
    if 'members' not in session:
        session['members'] = []

    current_squad = session.get('current_squad_name', 'Squad desconhecida')
    members_from_file = session.get('squad_members_from_file', [])
    total_file_cost = session.get('squad_total_cost', 0)

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
            members = session.get('members', [])
            members.append({
                'role': role,
                'function': function,
                'salary': salary,
                'hourly': hourly,
                'source': 'manual',
            })
            session['members'] = members
            session.modified = True

    members = session.get('members', [])
    
    # Calcular custo de membros adicionados manualmente
    manual_cost = sum(m['salary'] + 160 * m['hourly'] for m in members)
    
    # Custo total = arquivo + manual
    squad_cost = total_file_cost + manual_cost
    
    session['squad_cost'] = squad_cost
    session.modified = True

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
    if 'squad_cost' not in session or session.get('squad_cost', 0) <= 0:
        return redirect(url_for('routes.setup'))

    # Inicializar releases se não existir
    if 'releases' not in session:
        session['releases'] = []

    # Normalizar releases (converter antigas para novo formato)
    releases_raw = normalize_releases(session.get('releases', []))
    session['releases'] = releases_raw
    session.modified = True

    # Inicializar histórico
    if 'history' not in session:
        session['history'] = []

    # Processar criação de releases
    if request.method == 'POST' and 'create_releases' in request.form:
        num_releases = int(request.form.get('num_releases', 1))
        # Criar releases com pontos padrão de 50 pontos e 5 sprints cada
        session['releases'] = [
            {'points': 50, 'sprints': 5} for _ in range(num_releases)
        ]
        session.modified = True

    squad_cost = session.get('squad_cost', 0)
    current_squad = session.get('current_squad_name', 'Squad')
    releases = list(enumerate(session.get('releases', []), 1))  # (número, dicionário)
    total_points = sum(r[1]['points'] for r in releases) if releases else 0
    total_sprints = sum(r[1]['sprints'] for r in releases) if releases else 0
    
    value_per_point = squad_cost / total_points if total_points > 0 else 0
    bac = squad_cost

    history = session.get('history', [])
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

    return render_template(
        'plan.html',
        current_squad=current_squad,
        squad_cost=squad_cost,
        value_per_point=value_per_point,
        bac=bac,
        releases=releases,
        total_points=total_points,
        total_sprints=total_sprints,
        current_sprint=current_sprint,
        history=history,
        last_metrics=last_metrics,
    )


@routes_bp.route('/update_release_points', methods=['POST'])
def update_release_points():
    """Atualiza os pontos de uma release."""
    releases = normalize_releases(session.get('releases', []))
    release_index = int(request.form.get('release_index', 0))
    new_points = float(request.form.get('release_points', 50))
    
    if 0 <= release_index < len(releases):
        releases[release_index]['points'] = new_points
        session['releases'] = releases
        session.modified = True
        flash(f"Release {release_index + 1} atualizada para {new_points} pontos.", 'success')
    else:
        flash('Índice de release inválido.', 'error')
    
    return redirect(url_for('routes.plan'))


@routes_bp.route('/update_release_sprints', methods=['POST'])
def update_release_sprints():
    """Atualiza o número de sprints de uma release."""
    releases = normalize_releases(session.get('releases', []))
    release_index = int(request.form.get('release_index', 0))
    new_sprints = int(request.form.get('release_sprints', 5))
    
    if 0 <= release_index < len(releases):
        releases[release_index]['sprints'] = new_sprints
        session['releases'] = releases
        session.modified = True
        flash(f"Release {release_index + 1} atualizada para {new_sprints} sprints.", 'success')
    else:
        flash('Índice de release inválido.', 'error')
    
    return redirect(url_for('routes.plan'))


@routes_bp.route('/add_release', methods=['POST'])
def add_release():
    """Adiciona uma nova release."""
    releases = normalize_releases(session.get('releases', []))
    new_release_points = float(request.form.get('new_release_points', 50))
    new_release_sprints = int(request.form.get('new_release_sprints', 5))
    
    releases.append({
        'points': new_release_points,
        'sprints': new_release_sprints
    })
    session['releases'] = releases
    session.modified = True
    flash(f"Nova release adicionada com {new_release_points} pontos e {new_release_sprints} sprints.", 'success')
    
    return redirect(url_for('routes.plan'))


@routes_bp.route('/delete_release', methods=['POST'])
def delete_release():
    """Remove uma release."""
    releases = normalize_releases(session.get('releases', []))
    release_index = int(request.form.get('release_index', 0))
    
    if 0 <= release_index < len(releases):
        removed = releases.pop(release_index)
        session['releases'] = releases
        session.modified = True
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
    if 'squad_cost' not in session or session.get('squad_cost', 0) <= 0:
        return redirect(url_for('routes.setup'))

    releases = normalize_releases(session.get('releases', []))
    
    # Se não houver releases definidas, redirecionar para criar
    if not releases:
        flash('Por favor, configure as releases primeiro.', 'warning')
        return redirect(url_for('routes.plan'))
    
    squad_cost = session.get('squad_cost', 0)
    total_release_points = sum(r['points'] for r in releases)

    # Obter dados do formulário e converter formato brasileiro
    try:
        sprint_plan_points = float(request.form.get('sprint_plan_points', 0))
        sprint_done_points = float(request.form.get('sprint_done_points', 0))
        sprint_added_points = float(request.form.get('sprint_added_points', 0))
        sprint_planned_value = parse_brazilian_float(request.form.get('sprint_planned_value', 0))
        sprint_sprint_cost = parse_brazilian_float(request.form.get('sprint_sprint_cost', 0))
        sprint_actual_cost = parse_brazilian_float(request.form.get('sprint_actual_cost', 0))
    except (ValueError, TypeError):
        flash('Erro ao processar os valores inseridos.', 'error')
        return redirect(url_for('routes.plan'))

    # Adicionar ao histórico
    history = session.get('history', [])
    sprint_number = len(history) + 1
    
    # Cálculos de EVM usando os valores inseridos diretamente
    pv = sprint_planned_value  # Planned Value (valor planejado) - inserido pelo usuário
    ev = sprint_sprint_cost    # Earned Value (custo da sprint realizada) - inserido pelo usuário
    ac = sprint_actual_cost    # Actual Cost (custo real) - inserido pelo usuário
    
    cv = ev - ac  # Cost Variance
    sv = ev - pv  # Schedule Variance
    cpi = ev / ac if ac > 0 else 0  # Cost Performance Index
    spi = ev / pv if pv > 0 else 0  # Schedule Performance Index
    
    # Determinar status
    if cpi >= 1 and spi >= 1:
        status = "✓ OK"
    elif cpi < 1 and spi < 1:
        status = "⚠️ Acima do custo e atrasado"
    elif cpi < 1:
        status = "⚠️ Acima do custo"
    else:
        status = "⚠️ Atrasado"
    
    # Calcular porcentagem concluída do projeto
    total_history_done_points = sum(h.get('done_points', 0) for h in history)
    total_done_points = total_history_done_points + sprint_done_points
    project_completion_percentage = (total_done_points / total_release_points * 100) if total_release_points > 0 else 0

    record = {
        'sprint_no': sprint_number,
        'plan_points': sprint_plan_points,
        'done_points': sprint_done_points,
        'added_points': sprint_added_points,
        'PV': pv,
        'EV': ev,
        'AC': ac,
        'CV': cv,
        'SV': sv,
        'CPI': round(cpi, 2),
        'SPI': round(spi, 2),
        'status': status,
        'completion_percentage': round(project_completion_percentage, 2),
    }

    history.append(record)
    session['history'] = history
    session.modified = True
    
    flash(f'Sprint {sprint_number} registrada com sucesso!', 'success')

    return redirect(url_for('routes.plan'))


@routes_bp.route('/generate_chart')
def generate_chart():
    """Gera um gráfico cumulativo com AC, EV e CV de todas as sprints."""
    history = session.get('history', [])
    
    if not history:
        # Retornar imagem em branco se não há histórico
        return send_file(io.BytesIO(), mimetype='image/png')
    
    # Extrair dados do histórico
    sprints = [str(record['sprint_no']) for record in history]
    ac_values = [record['AC'] for record in history]
    ev_values = [record['EV'] for record in history]
    cv_values = [record['CV'] for record in history]
    
    # Calcular valores cumulativos
    ac_cumulative = []
    ev_cumulative = []
    cumsum_ac = 0
    cumsum_ev = 0
    
    for ac, ev in zip(ac_values, ev_values):
        cumsum_ac += ac
        cumsum_ev += ev
        ac_cumulative.append(cumsum_ac)
        ev_cumulative.append(cumsum_ev)
    
    # Criar figura
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plotar linhas
    ax.plot(sprints, ac_cumulative, marker='o', label='AC Cumulativo', linewidth=2, color='#e74c3c')
    ax.plot(sprints, ev_cumulative, marker='s', label='EV Cumulativo', linewidth=2, color='#27ae60')
    ax.plot(sprints, cv_values, marker='^', label='CV (Variação de Custo)', linewidth=2, color='#3498db', linestyle='--')
    
    # Configurar eixos
    ax.set_xlabel('Sprint', fontsize=12, fontweight='bold')
    ax.set_ylabel('Valor (R$)', fontsize=12, fontweight='bold')
    ax.set_title('Gráfico Cumulativo - AC, EV e Variação de Custo', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Formatar eixo Y como moeda
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'R$ {x:,.0f}'))
    
    # Salvar em bytesio
    img = io.BytesIO()
    plt.tight_layout()
    plt.savefig(img, format='png', dpi=100, bbox_inches='tight')
    img.seek(0)
    plt.close()
    
    return send_file(img, mimetype='image/png')


@routes_bp.route('/remove_member/<int:member_index>', methods=['POST'])
def remove_member(member_index):
    """
    Remove um membro adicionado manualmente da squad.
    """
    members = session.get('members', [])
    
    if 0 <= member_index < len(members):
        removed = members.pop(member_index)
        session['members'] = members
        session.modified = True
        flash(f"Membro '{removed['role']}' removido com sucesso.", 'success')
    else:
        flash('Índice de membro inválido.', 'error')
    
    return redirect(url_for('routes.setup'))


@routes_bp.route('/remove_file_member/<int:member_index>', methods=['POST'])
def remove_file_member(member_index):
    """
    Remove um membro carregado da planilha da squad.
    """
    file_members = session.get('squad_members_from_file', [])
    
    if 0 <= member_index < len(file_members):
        removed = file_members.pop(member_index)
        session['squad_members_from_file'] = file_members
        # Recalcular o custo total da planilha
        session['squad_total_cost'] = sum(member['total_grupo'] for member in file_members)
        session.modified = True
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

