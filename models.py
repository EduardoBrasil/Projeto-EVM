"""
models.py - Logica de negocio para EVM (Earned Value Management).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


class TeamMember:
    """Representa um membro da squad."""

    def __init__(self, role: str, function: str, salary: float, hourly_rate: float):
        self.role = role
        self.function = function
        self.salary = salary
        self.hourly_rate = hourly_rate

    def calculate_cost(self, hours_per_period: float = 160) -> float:
        return self.salary + (hours_per_period * self.hourly_rate)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "function": self.function,
            "salary": self.salary,
            "hourly": self.hourly_rate,
        }


class Squad:
    """Gerencia os membros da squad e calcula o custo total."""

    def __init__(self):
        self.members = []

    def add_member(self, role: str, function: str, salary: float, hourly_rate: float) -> None:
        self.members.append(TeamMember(role, function, salary, hourly_rate))

    def get_total_cost(self, hours_per_period: float = 160) -> float:
        return sum(member.calculate_cost(hours_per_period) for member in self.members)

    def get_members_list(self) -> list:
        return [member.to_dict() for member in self.members]


class SquadLoader:
    """Carrega dados de squads de arquivo Excel/CSV."""

    EXPECTED_COLUMNS = ["SQUAD", "CARGO", "ÁREA", "QTDE", "Custo M H/H", "Preço M/HH", "TOTAL GRUPO"]
    CURRENCY_PATTERN = re.compile(r"[R$€£¥₹₽₩₦₪₫₴₸₺₱₭₮₯₰₳₶₷₻₽₾₿]")

    @classmethod
    def load_file(cls, file_path: str) -> dict:
        data_frame = cls._read_file(file_path)
        data_frame.columns = data_frame.columns.str.strip()

        missing_cols = [column for column in cls.EXPECTED_COLUMNS if column not in data_frame.columns]
        if missing_cols:
            raise ValueError(f"Colunas faltando: {', '.join(missing_cols)}")

        squads_dict = {}
        for squad_name, group in data_frame.groupby("SQUAD"):
            members = []
            total_group_cost = 0

            for _, row in group.iterrows():
                try:
                    member_data = {
                        "cargo": str(row["CARGO"]).strip(),
                        "area": str(row["ÁREA"]).strip(),
                        "qtde": cls.safe_float(row["QTDE"]),
                        "custo_mhh": cls.safe_float(row["Custo M H/H"]),
                        "preco_mhh": cls.safe_float(row["Preço M/HH"]),
                        "total_grupo": 0,
                    }
                except ValueError as exc:
                    raise ValueError(f"Erro na linha da squad '{squad_name}': {exc}") from exc

                total_grupo = member_data["qtde"] * member_data["preco_mhh"] * 8 * 5 * 4.2
                member_data["total_grupo"] = total_grupo
                members.append(member_data)
                total_group_cost += total_grupo

            squads_dict[squad_name] = {
                "members": members,
                "total_cost": total_group_cost,
            }

        return squads_dict

    @staticmethod
    def _read_file(file_path: str) -> pd.DataFrame:
        if file_path.endswith(".xlsx"):
            return pd.read_excel(file_path, dtype=str)

        encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
        for encoding in encodings:
            try:
                return pd.read_csv(file_path, encoding=encoding, dtype=str)
            except (UnicodeDecodeError, LookupError):
                continue
        raise ValueError(f"Não foi possível decodificar o arquivo com codificações: {encodings}")

    @classmethod
    def safe_float(cls, value):
        if not isinstance(value, str):
            try:
                return float(value)
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"Valor inválido para campo numérico: '{value}' (esperado número)"
                ) from exc

        cleaned_value = cls.CURRENCY_PATTERN.sub("", value).strip().replace(" ", "")

        try:
            return float(cleaned_value)
        except (ValueError, TypeError):
            pass

        if "," in cleaned_value and "." in cleaned_value:
            last_comma = cleaned_value.rfind(",")
            last_dot = cleaned_value.rfind(".")
            if last_comma > last_dot:
                candidate = cleaned_value.replace(".", "").replace(",", ".")
            else:
                candidate = cleaned_value.replace(",", "")
            try:
                return float(candidate)
            except (ValueError, TypeError):
                pass
        elif "," in cleaned_value:
            if cleaned_value.count(",") == 1 and len(cleaned_value.split(",")[1]) == 2:
                candidate = cleaned_value.replace(",", "")
            else:
                candidate = cleaned_value.replace(".", "").replace(",", ".")
            try:
                return float(candidate)
            except (ValueError, TypeError):
                pass
        elif "." in cleaned_value:
            try:
                return float(cleaned_value.replace(",", ""))
            except (ValueError, TypeError):
                pass

        try:
            return float(cleaned_value.replace(",", "."))
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Valor inválido para campo numérico: '{value}' (esperado número)"
            ) from exc

    @staticmethod
    def create_template(output_path: str = "template_squads.xlsx") -> str:
        data_frame = pd.DataFrame(
            {
                "SQUAD": ["Squad A", "Squad A", "Squad B", "Squad B"],
                "CARGO": ["Developer Senior", "Developer Junior", "DevOps", "QA"],
                "ÁREA": ["Backend", "Frontend", "Infraestrutura", "Qualidade"],
                "QTDE": [2, 3, 1, 2],
                "Custo M H/H": [5000, 3000, 4000, 2500],
                "Preço M/HH": [500, 300, 400, 250],
                "TOTAL GRUPO": [10000, 9000, 4000, 5000],
            }
        )
        data_frame.to_excel(output_path, index=False)
        return output_path


class EVMCalculator:
    """Calcula métricas de Earned Value Management."""

    @staticmethod
    def calculate_pv(planned_points: float, value_per_point: float) -> float:
        return planned_points * value_per_point

    @staticmethod
    def calculate_ev(earned_points: float, value_per_point: float) -> float:
        return earned_points * value_per_point

    @staticmethod
    def calculate_cv(ev: float, ac: float) -> float:
        return ev - ac

    @staticmethod
    def calculate_sv(ev: float, pv: float) -> float:
        return ev - pv

    @staticmethod
    def calculate_cpi(ev: float, ac: float) -> float:
        return ev / ac if ac > 0 else 0

    @staticmethod
    def calculate_spi(ev: float, pv: float) -> float:
        return ev / pv if pv > 0 else 0

    @staticmethod
    def get_status(cpi: float, spi: float) -> str:
        if cpi >= 1 and spi >= 1:
            return "✓ OK"
        if cpi < 1 and spi < 1:
            return "⚠️ Atenção: Acima do custo e atrasado"
        if cpi < 1:
            return "⚠️ Atenção: Acima do custo"
        return "⚠️ Atenção: Atrasado"

    @classmethod
    def calculate_sprint_metrics(
        cls,
        planned_points: float,
        earned_points: float,
        actual_cost: float,
        value_per_point: float,
    ) -> dict:
        pv = cls.calculate_pv(planned_points, value_per_point)
        ev = cls.calculate_ev(earned_points, value_per_point)
        cv = cls.calculate_cv(ev, actual_cost)
        sv = cls.calculate_sv(ev, pv)
        cpi = cls.calculate_cpi(ev, actual_cost)
        spi = cls.calculate_spi(ev, pv)
        return {
            "PV": pv,
            "EV": ev,
            "AC": actual_cost,
            "CV": cv,
            "SV": sv,
            "CPI": cpi,
            "SPI": spi,
            "status": cls.get_status(cpi, spi),
        }
