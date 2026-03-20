"""
charts.py - Builders para graficos do projeto.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


class BaseChartBuilder(ABC):
    """Template Method para construcao de graficos."""

    def build(self, history):
        fig, ax = plt.subplots(figsize=self.figure_size())
        if not history:
            ax.text(0.5, 0.5, "Sem dados para exibir", ha="center", va="center", fontsize=14, color="#7f8c8d")
            ax.axis("off")
            return fig

        self.plot(ax, history)
        ax.grid(True, alpha=0.3)
        return fig

    def figure_size(self):
        return (12, 5)

    @abstractmethod
    def plot(self, ax, history):
        """Desenha o grafico."""


class CumulativeChartBuilder(BaseChartBuilder):
    """Builder do grafico cumulativo."""

    def figure_size(self):
        return (12, 6)

    def plot(self, ax, history):
        sprints = [str(record["sprint_no"]) for record in history]
        pv_values = [record["PV"] for record in history]
        ac_values = [record["AC"] for record in history]
        ev_values = [record["EV"] for record in history]

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

        ax.plot(sprints, ac_cumulative, marker="o", label="AC Cumulativo", linewidth=2.4, color="#e74c3c", zorder=2)
        ax.plot(sprints, ev_cumulative, marker="s", label="EV Cumulativo", linewidth=2.4, color="#27ae60", zorder=3)
        ax.plot(sprints, pv_cumulative, marker="D", label="PV Cumulativo", linewidth=3.2, color="#f39c12", linestyle="-.", zorder=4)
        ax.scatter(sprints, pv_cumulative, color="#f39c12", edgecolors="white", linewidths=1.1, s=70, zorder=5)
        ax.set_xlabel("Sprint", fontsize=12, fontweight="bold")
        ax.set_ylabel("Valor (R$)", fontsize=12, fontweight="bold")
        ax.set_title("Gráfico Cumulativo - PV, EV e AC", fontsize=14, fontweight="bold")
        ax.legend(loc="best", fontsize=10)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"R$ {x:,.0f}"))


class IndexChartBuilder(BaseChartBuilder):
    """Builder reutilizavel para graficos de indice."""

    def __init__(self, key, color, marker, title):
        self.key = key
        self.color = color
        self.marker = marker
        self.title = title

    def plot(self, ax, history):
        sprints = [str(record["sprint_no"]) for record in history]
        values = [record[self.key] for record in history]
        ax.plot(sprints, values, marker=self.marker, linewidth=2, color=self.color, label=self.key)
        ax.axhline(1, color="#7f8c8d", linestyle="--", linewidth=1, label="Referência = 1")
        ax.set_xlabel("Sprint", fontsize=12, fontweight="bold")
        ax.set_ylabel(self.key, fontsize=12, fontweight="bold")
        ax.set_title(self.title, fontsize=14, fontweight="bold")
        ax.legend(loc="best", fontsize=10)


class ChartBuilderFactory:
    """Factory Method para builders de grafico."""

    def __init__(self):
        self.builders = {
            "cumulative": CumulativeChartBuilder(),
            "cpi": IndexChartBuilder("CPI", "#3498db", "^", "Gráfico de CPI - Cost Performance Index"),
            "spi": IndexChartBuilder("SPI", "#8e44ad", "v", "Gráfico de SPI - Schedule Performance Index"),
        }

    def create(self, chart_type):
        return self.builders[chart_type]
