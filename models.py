"""
models.py - Lógica de negócio para EVM (Earned Value Management)
"""

import pandas as pd
from pathlib import Path


class TeamMember:
    """Representa um membro da squad."""

    def __init__(self, role: str, function: str, salary: float, hourly_rate: float):
        self.role = role
        self.function = function
        self.salary = salary
        self.hourly_rate = hourly_rate

    def calculate_cost(self, hours_per_period: float = 160) -> float:
        """
        Calcula o custo estimado do membro.
        
        Args:
            hours_per_period: Horas consideradas no período (default 160h/mês)
        
        Returns:
            Custo total (salário + horas * valor/hora)
        """
        return self.salary + (hours_per_period * self.hourly_rate)

    def to_dict(self) -> dict:
        """Converte membro para dicionário."""
        return {
            "role": self.role,
            "function": self.function,
            "salary": self.salary,
            "hourly": self.hourly_rate,
        }


class Squad:
    """Gerencia os membros da squad e calcula custo total."""

    def __init__(self):
        self.members = []

    def add_member(self, role: str, function: str, salary: float, hourly_rate: float) -> None:
        """Adiciona um membro à squad."""
        member = TeamMember(role, function, salary, hourly_rate)
        self.members.append(member)

    def get_total_cost(self, hours_per_period: float = 160) -> float:
        """Calcula o custo total da squad."""
        return sum(member.calculate_cost(hours_per_period) for member in self.members)

    def get_members_list(self) -> list:
        """Retorna lista de membros em formato dicionário."""
        return [member.to_dict() for member in self.members]


class SquadLoader:
    """Carrega dados de squads de arquivo Excel/CSV."""

    EXPECTED_COLUMNS = ['SQUAD', 'CARGO', 'ÁREA', 'QTDE', 'Custo M H/H', 'Preço M/HH', 'TOTAL GRUPO']

    @staticmethod
    def load_file(file_path: str) -> dict:
        """
        Carrega arquivo Excel/CSV com dados de squads.
        
        Args:
            file_path: Caminho para o arquivo
        
        Returns:
            Dicionário com squads organizadas por nome
        
        Raises:
            ValueError: Se arquivo não contém as colunas esperadas ou dados inválidos
        """
        if file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path, dtype=str)
        else:
            # Tentar múltiplas codificações para CSV
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            df = None
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, dtype=str)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            
            if df is None:
                raise ValueError(f'Não foi possível decodificar o arquivo com codificações: {encodings}')

        # Normalizar nomes de colunas (remover espaços extras)
        df.columns = df.columns.str.strip()

        # Validar colunas
        missing_cols = [col for col in SquadLoader.EXPECTED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Colunas faltando: {', '.join(missing_cols)}")

        # Função auxiliar para conversão segura
        def safe_int(value):
            try:
                # Primeiro tentar converter diretamente
                if isinstance(value, str):
                    # Remover símbolos de moeda se presentes
                    import re
                    value = re.sub(r'[R$€£$¥₹₽₩₦₨₪₫₡₵₺₴₸₼₲₱₭₯₰₳₶₷₹₻₽₾₿]', '', value).strip()
                    value = value.replace(' ', '')
                return int(float(value))  # Primeiro para float para lidar com '1.0'
            except (ValueError, TypeError):
                raise ValueError(f"Valor inválido para QTDE: '{value}' (esperado número inteiro)")

        def safe_float(value):
            if not isinstance(value, str):
                try:
                    return float(value)
                except (ValueError, TypeError):
                    raise ValueError(f"Valor inválido para campo numérico: '{value}' (esperado número)")
            
            # Remover símbolos de moeda comuns
            import re
            value = re.sub(r'[R$€£$¥₹₽₩₦₨₪₫₡₵₺₴₸₼₲₱₭₯₰₳₶₷₹₻₽₾₿]', '', value).strip()
            
            # Remover espaços
            value = value.replace(' ', '')
            
            # Tentar conversão direta
            try:
                return float(value)
            except (ValueError, TypeError):
                pass
            
            # Detectar formato baseado nos separadores
            if ',' in value and '.' in value:
                # Tem ambos separadores
                last_comma = value.rfind(',')
                last_dot = value.rfind('.')
                if last_comma > last_dot:
                    # Último separador é ',', formato brasileiro
                    cleaned = value.replace('.', '').replace(',', '.')
                    try:
                        return float(cleaned)
                    except (ValueError, TypeError):
                        pass
                else:
                    # Último separador é '.', formato americano
                    cleaned = value.replace(',', '')
                    try:
                        return float(cleaned)
                    except (ValueError, TypeError):
                        pass
            elif ',' in value:
                # Só tem ','
                if value.count(',') == 1 and len(value.split(',')[1]) == 2:
                    # Provavelmente formato americano com ',' como separador de milhares
                    cleaned = value.replace(',', '')
                    try:
                        return float(cleaned)
                    except (ValueError, TypeError):
                        pass
                else:
                    # Provavelmente formato brasileiro
                    cleaned = value.replace('.', '').replace(',', '.')
                    try:
                        return float(cleaned)
                    except (ValueError, TypeError):
                        pass
            elif '.' in value:
                # Só tem '.', formato americano
                cleaned = value.replace(',', '')
                try:
                    return float(cleaned)
                except (ValueError, TypeError):
                    pass
            
            # Fallback: tentar substituir ',' por '.'
            try:
                return float(value.replace(',', '.'))
            except (ValueError, TypeError):
                raise ValueError(f"Valor inválido para campo numérico: '{value}' (esperado número)")

        # Agrupar por SQUAD
        squads_dict = {}
        for squad_name, group in df.groupby('SQUAD'):
            members = []
            total_group_cost = 0

            for _, row in group.iterrows():
                try:
                    member_data = {
                        'cargo': str(row['CARGO']).strip(),
                        'area': str(row['ÁREA']).strip(),
                        'qtde': safe_float(row['QTDE']),
                        'custo_mhh': safe_float(row['Custo M H/H']),
                        'preco_mhh': safe_float(row['Preço M/HH']),
                        'total_grupo': 0,  # Será calculado abaixo
                    }
                    # Calcular total_grupo baseado na quantidade e horas trabalhadas
                    # preco_mhh é o preço por hora, multiplicado por 8h/dia * 5 dias/semana * 4.2 semanas/mês
                    total_grupo = member_data['qtde'] * member_data['preco_mhh'] * 8 * 5 * 4.2
                    member_data['total_grupo'] = total_grupo
                    members.append(member_data)
                    total_group_cost += member_data['total_grupo']
                except ValueError as e:
                    raise ValueError(f"Erro na linha da squad '{squad_name}': {str(e)}")

            squads_dict[squad_name] = {
                'members': members,
                'total_cost': total_group_cost,
            }

        return squads_dict

    @staticmethod
    def create_template(output_path: str = 'template_squads.xlsx') -> str:
        """
        Cria um arquivo template para preenchimento.
        
        Args:
            output_path: Caminho onde salvar o template
        
        Returns:
            Caminho do arquivo criado
        """
        data = {
            'SQUAD': ['Squad A', 'Squad A', 'Squad B', 'Squad B'],
            'CARGO': ['Developer Senior', 'Developer Junior', 'DevOps', 'QA'],
            'ÁREA': ['Backend', 'Frontend', 'Infraestrutura', 'Qualidade'],
            'QTDE': [2, 3, 1, 2],
            'Custo M H/H': [5000, 3000, 4000, 2500],
            'Preço M/HH': [500, 300, 400, 250],
            'TOTAL GRUPO': [10000, 9000, 4000, 5000],
        }

        df = pd.DataFrame(data)
        df.to_excel(output_path, index=False)
        return output_path


class EVMCalculator:
    """Calcula métricas de Earned Value Management."""

    @staticmethod
    def calculate_pv(planned_points: float, value_per_point: float) -> float:
        """
        Planned Value - Valor planejado.
        
        Args:
            planned_points: Pontos planejados
            value_per_point: Valor por ponto
        
        Returns:
            PV em reais
        """
        return planned_points * value_per_point

    @staticmethod
    def calculate_ev(earned_points: float, value_per_point: float) -> float:
        """
        Earned Value - Valor agregado.
        
        Args:
            earned_points: Pontos concluídos
            value_per_point: Valor por ponto
        
        Returns:
            EV em reais
        """
        return earned_points * value_per_point

    @staticmethod
    def calculate_cv(ev: float, ac: float) -> float:
        """
        Cost Variance - Variação de custo.
        CV = EV - AC
        
        Positivo = abaixo do orçamento
        Negativo = acima do orçamento
        """
        return ev - ac

    @staticmethod
    def calculate_sv(ev: float, pv: float) -> float:
        """
        Schedule Variance - Variação de prazo.
        SV = EV - PV
        
        Positivo = à frente do cronograma
        Negativo = atrasado no cronograma
        """
        return ev - pv

    @staticmethod
    def calculate_cpi(ev: float, ac: float) -> float:
        """
        Cost Performance Index - Índice de desempenho de custo.
        CPI = EV / AC
        
        > 1 = eficiente em custo
        = 1 = conforme orçamento
        < 1 = acima do orçamento
        """
        return ev / ac if ac > 0 else 0

    @staticmethod
    def calculate_spi(ev: float, pv: float) -> float:
        """
        Schedule Performance Index - Índice de desempenho de prazo.
        SPI = EV / PV
        
        > 1 = à frente do cronograma
        = 1 = conforme cronograma
        < 1 = atrasado no cronograma
        """
        return ev / pv if pv > 0 else 0

    @staticmethod
    def get_status(cpi: float, spi: float) -> str:
        """
        Determina o status da sprint baseado em CPI e SPI.
        
        Args:
            cpi: Cost Performance Index
            spi: Schedule Performance Index
        
        Returns:
            Status descritivo
        """
        if cpi >= 1 and spi >= 1:
            return "✓ OK"
        elif cpi < 1 and spi < 1:
            return "⚠️ Atenção: Acima do custo e atrasado"
        elif cpi < 1:
            return "⚠️ Atenção: Acima do custo"
        else:
            return "⚠️ Atenção: Atrasado"

    @classmethod
    def calculate_sprint_metrics(
        cls, 
        planned_points: float, 
        earned_points: float, 
        actual_cost: float, 
        value_per_point: float
    ) -> dict:
        """
        Calcula todas as métricas de uma sprint.
        
        Args:
            planned_points: Pontos planejados
            earned_points: Pontos concluídos
            actual_cost: Custo real
            value_per_point: Valor por ponto
        
        Returns:
            Dicionário com todas as métricas
        """
        pv = cls.calculate_pv(planned_points, value_per_point)
        ev = cls.calculate_ev(earned_points, value_per_point)
        cv = cls.calculate_cv(ev, actual_cost)
        sv = cls.calculate_sv(ev, pv)
        cpi = cls.calculate_cpi(ev, actual_cost)
        spi = cls.calculate_spi(ev, pv)
        status = cls.get_status(cpi, spi)

        return {
            "PV": pv,
            "EV": ev,
            "AC": actual_cost,
            "CV": cv,
            "SV": sv,
            "CPI": cpi,
            "SPI": spi,
            "status": status,
        }

    """Calcula métricas de Earned Value Management."""

    @staticmethod
    def calculate_pv(planned_points: float, value_per_point: float) -> float:
        """
        Planned Value - Valor planejado.
        
        Args:
            planned_points: Pontos planejados
            value_per_point: Valor por ponto
        
        Returns:
            PV em reais
        """
        return planned_points * value_per_point

    @staticmethod
    def calculate_ev(earned_points: float, value_per_point: float) -> float:
        """
        Earned Value - Valor agregado.
        
        Args:
            earned_points: Pontos concluídos
            value_per_point: Valor por ponto
        
        Returns:
            EV em reais
        """
        return earned_points * value_per_point

    @staticmethod
    def calculate_cv(ev: float, ac: float) -> float:
        """
        Cost Variance - Variação de custo.
        CV = EV - AC
        
        Positivo = abaixo do orçamento
        Negativo = acima do orçamento
        """
        return ev - ac

    @staticmethod
    def calculate_sv(ev: float, pv: float) -> float:
        """
        Schedule Variance - Variação de prazo.
        SV = EV - PV
        
        Positivo = à frente do cronograma
        Negativo = atrasado no cronograma
        """
        return ev - pv

    @staticmethod
    def calculate_cpi(ev: float, ac: float) -> float:
        """
        Cost Performance Index - Índice de desempenho de custo.
        CPI = EV / AC
        
        > 1 = eficiente em custo
        = 1 = conforme orçamento
        < 1 = acima do orçamento
        """
        return ev / ac if ac > 0 else 0

    @staticmethod
    def calculate_spi(ev: float, pv: float) -> float:
        """
        Schedule Performance Index - Índice de desempenho de prazo.
        SPI = EV / PV
        
        > 1 = à frente do cronograma
        = 1 = conforme cronograma
        < 1 = atrasado no cronograma
        """
        return ev / pv if pv > 0 else 0

    @staticmethod
    def get_status(cpi: float, spi: float) -> str:
        """
        Determina o status da sprint baseado em CPI e SPI.
        
        Args:
            cpi: Cost Performance Index
            spi: Schedule Performance Index
        
        Returns:
            Status descritivo
        """
        if cpi >= 1 and spi >= 1:
            return "✓ OK"
        elif cpi < 1 and spi < 1:
            return "⚠️ Atenção: Acima do custo e atrasado"
        elif cpi < 1:
            return "⚠️ Atenção: Acima do custo"
        else:
            return "⚠️ Atenção: Atrasado"

    @classmethod
    def calculate_sprint_metrics(
        cls, 
        planned_points: float, 
        earned_points: float, 
        actual_cost: float, 
        value_per_point: float
    ) -> dict:
        """
        Calcula todas as métricas de uma sprint.
        
        Args:
            planned_points: Pontos planejados
            earned_points: Pontos concluídos
            actual_cost: Custo real
            value_per_point: Valor por ponto
        
        Returns:
            Dicionário com todas as métricas
        """
        pv = cls.calculate_pv(planned_points, value_per_point)
        ev = cls.calculate_ev(earned_points, value_per_point)
        cv = cls.calculate_cv(ev, actual_cost)
        sv = cls.calculate_sv(ev, pv)
        cpi = cls.calculate_cpi(ev, actual_cost)
        spi = cls.calculate_spi(ev, pv)
        status = cls.get_status(cpi, spi)

        return {
            "PV": pv,
            "EV": ev,
            "AC": actual_cost,
            "CV": cv,
            "SV": sv,
            "CPI": cpi,
            "SPI": spi,
            "status": status,
        }
