"""
app.py - Aplicação Flask para EVM (Earned Value Management)

Arquitetura limpa separando:
- models.py: Lógica de negócio (Squad, TeamMember, EVMCalculator, SquadLoader)
- routes.py: Rotas e controllers
- templates/: Componentes HTML
- static/: CSS e assets

Autor: GitHub Copilot
Data: 2026
"""

import os
from flask import Flask, session
from routes import routes_bp

# Configuração da aplicação
app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

# Configurar pasta de uploads
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Criar pasta se não existir
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Registrar blueprints
app.register_blueprint(routes_bp)

# Filtro customizado para formatação de moeda brasileira
def format_currency(value):
    """Formata um valor numérico como moeda brasileira."""
    try:
        value = float(value)
        return f"R$ {value:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')
    except (ValueError, TypeError):
        return "R$ 0,00"

app.jinja_env.filters['currency'] = format_currency


@app.context_processor
def inject_navigation_context():
    """Disponibiliza contexto global para navegação lateral."""
    squads_data = session.get('squads_data', {})
    return {
        'nav_squads': list(squads_data.keys()),
        'nav_current_squad': session.get('current_squad_name'),
    }

if __name__ == '__main__':
    app.run(debug=True)
