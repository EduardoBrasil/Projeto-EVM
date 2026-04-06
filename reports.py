"""
reports.py - Geracao de relatorios executivos em PDF.
"""

from __future__ import annotations

import io
import textwrap
from datetime import datetime

import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.backends.backend_pdf import PdfPages

from charts import ChartBuilderFactory


chart_factory = ChartBuilderFactory()


class ExecutiveReportBuilder:
    def __init__(self):
        self.page_size = (8.27, 11.69)
        self.colors = {
            "bg": "#f5f1e8",
            "surface": "#fffdf8",
            "surface_alt": "#ece4d8",
            "text": "#1f2933",
            "muted": "#5b6670",
            "accent": "#0f4c5c",
            "accent_soft": "#d9e7ea",
            "green": "#2a9d5b",
            "yellow": "#d9a404",
            "red": "#c44536",
            "gray": "#cad1d7",
            "border": "#d7d0c4",
        }

    def _sanitize_text(self, value):
        sanitized = str(value or "-")
        replacements = {
            "ÃƒÂ¢Ã…Â¡Ã‚Â ÃƒÂ¯Ã‚Â¸Ã‚Â ": "",
            "ÃƒÂ¢Ã…â€œÃ¢â‚¬Å“ ": "",
            "AtenÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Â£o": "Atencao",
            "NÃƒÆ’Ã‚Â£o": "Nao",
        }
        for old, new in replacements.items():
            sanitized = sanitized.replace(old, new)
        return sanitized.encode("ascii", "ignore").decode("ascii")

    def _format_currency(self, value):
        return f"R$ {float(value or 0):,.2f}"

    def _risk_style(self, level):
        mapping = {
            "green": ("Baixo risco", self.colors["green"]),
            "yellow": ("Risco moderado", self.colors["yellow"]),
            "red": ("Alto risco", self.colors["red"]),
        }
        return mapping[level]

    def _project_risk_level(self, summary):
        projection = summary.get("projection") or {}
        delayed = projection.get("delay_sprints", 0) > 0
        over_budget = projection.get("cost_variance_at_completion", 0) > 0
        if delayed and over_budget:
            return "red"
        if delayed or over_budget:
            return "yellow"
        return "green"

    def _sprint_risk_level(self, record):
        cpi = float(record.get("CPI", 0) or 0)
        spi = float(record.get("SPI", 0) or 0)
        if cpi < 1 and spi < 1:
            return "red"
        if cpi < 1 or spi < 1:
            return "yellow"
        return "green"

    def _new_canvas(self, title, subtitle):
        fig = plt.figure(figsize=self.page_size, facecolor=self.colors["bg"])
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis("off")

        ax.add_patch(
            patches.FancyBboxPatch(
                (0.04, 0.91),
                0.92,
                0.07,
                boxstyle="round,pad=0.012,rounding_size=0.02",
                facecolor=self.colors["accent"],
                edgecolor=self.colors["accent"],
            )
        )
        ax.text(0.07, 0.953, title, color="white", fontsize=18, fontweight="bold", va="center")
        ax.text(0.07, 0.922, subtitle, color="#dbe7ea", fontsize=9, va="center")
        return fig, ax

    def _wrap_bullets(self, lines, width):
        bullets = []
        for line in lines:
            wrapped = textwrap.fill(
                self._sanitize_text(line),
                width=width,
                subsequent_indent="  ",
            )
            bullets.append(f"- {wrapped}")
        return "\n".join(bullets)

    def _truncate_text(self, value, max_chars=34):
        text = self._sanitize_text(value)
        if len(text) <= max_chars:
            return text
        return f"{text[: max_chars - 3].rstrip()}..."

    def _draw_info_band(self, ax, items, y=0.822, height=0.05):
        gap = 0.03
        width = (0.92 - (gap * (len(items) - 1))) / len(items)
        for index, (label, value) in enumerate(items):
            x = 0.04 + (index * (width + gap))
            ax.add_patch(
                patches.FancyBboxPatch(
                    (x, y),
                    width,
                    height,
                    boxstyle="round,pad=0.01,rounding_size=0.015",
                    facecolor=self.colors["surface_alt"],
                    edgecolor=self.colors["border"],
                )
            )
            ax.text(x + 0.015, y + height - 0.014, label, fontsize=7.8, color=self.colors["muted"], va="top")
            ax.text(
                x + 0.015,
                y + 0.012,
                self._truncate_text(value, max_chars=24),
                fontsize=9.2,
                color=self.colors["text"],
                va="bottom",
            )

    def _draw_metric_card(self, ax, x, y, w, h, label, value, tone="default", note=None):
        facecolor = self.colors["surface"]
        edgecolor = self.colors["border"]
        if tone == "green":
            facecolor = "#eef7f1"
            edgecolor = "#b8dcc3"
        elif tone == "yellow":
            facecolor = "#fbf6e4"
            edgecolor = "#e5d79f"
        elif tone == "red":
            facecolor = "#fbeceb"
            edgecolor = "#e1b4ad"

        ax.add_patch(
            patches.FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.01,rounding_size=0.018",
                facecolor=facecolor,
                edgecolor=edgecolor,
            )
        )

        display_value = self._sanitize_text(value)
        value_font = 15 if len(display_value) <= 18 else 11
        ax.text(x + 0.02, y + h - 0.03, label, fontsize=8.5, color=self.colors["muted"], va="top")
        ax.text(
            x + 0.02,
            y + 0.045,
            display_value,
            fontsize=value_font,
            color=self.colors["text"],
            fontweight="bold",
            va="bottom",
        )
        if note:
            ax.text(x + 0.02, y + 0.018, self._sanitize_text(note), fontsize=7.5, color=self.colors["muted"], va="bottom")

    def _draw_semaphore(self, ax, x, y, active_level):
        levels = [("red", -0.02), ("yellow", 0.0), ("green", 0.02)]
        for level, offset in levels:
            color = self.colors[level] if level == active_level else self.colors["gray"]
            ax.add_patch(patches.Circle((x + offset, y), 0.0075, color=color))

    def _draw_risk_panel(self, ax, x, y, w, h, title, level, status_text):
        risk_label, _ = self._risk_style(level)
        ax.add_patch(
            patches.FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.01,rounding_size=0.02",
                facecolor=self.colors["surface"],
                edgecolor=self.colors["border"],
            )
        )
        ax.text(x + 0.02, y + h - 0.03, title, fontsize=9.5, color=self.colors["muted"], va="top")
        center_x = x + (w / 2)
        self._draw_semaphore(ax, center_x, y + 0.075, level)
        ax.text(center_x, y + 0.048, risk_label, fontsize=10.5, color=self.colors["text"], fontweight="bold", va="center", ha="center")
        ax.text(
            center_x,
            y + 0.022,
            self._truncate_text(status_text, max_chars=46),
            fontsize=7.4,
            color=self.colors["muted"],
            va="center",
            ha="center",
        )

    def _draw_text_box(self, ax, x, y, w, h, title, lines, width=52):
        ax.add_patch(
            patches.FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.012,rounding_size=0.018",
                facecolor=self.colors["surface"],
                edgecolor=self.colors["border"],
            )
        )
        ax.text(x + 0.02, y + h - 0.03, title, fontsize=10.5, color=self.colors["accent"], fontweight="bold", va="top")
        ax.text(
            x + 0.02,
            y + h - 0.07,
            self._wrap_bullets(lines, width=width),
            fontsize=8.6,
            color=self.colors["text"],
            va="top",
            linespacing=1.35,
        )

    def build_sprint_report(self, summary):
        return self.build_project_report(summary)

    def build_project_report(self, summary):
        buffer = io.BytesIO()
        with PdfPages(buffer) as pdf:
            pdf.savefig(self._build_project_summary_page(summary), bbox_inches="tight")
            pdf.savefig(self._build_project_insights_page(summary), bbox_inches="tight")
            for sprint_page in self._build_sprint_evolution_pages(summary):
                pdf.savefig(sprint_page, bbox_inches="tight")
            history = summary.get("history", [])
            pdf.savefig(chart_factory.create("cumulative").build(history), bbox_inches="tight")
            pdf.savefig(chart_factory.create("cpi").build(history), bbox_inches="tight")
            pdf.savefig(chart_factory.create("spi").build(history), bbox_inches="tight")
        buffer.seek(0)
        return buffer

    def _project_executive_summary(self, summary):
        projection = summary.get("projection") or {}
        baseline_comparison = summary.get("baseline_comparison") or {}
        delay = float(projection.get("delay_sprints", 0) or 0)
        cost_variance = float(projection.get("cost_variance_at_completion", 0) or 0)
        scope_delta = float(baseline_comparison.get("scope_delta", 0) or 0)
        remaining = float(projection.get("projected_remaining_sprints", 0) or 0)
        done_points = sum(float(item.get("done_points", 0) or 0) for item in summary.get("history", []))

        lines = [
            f"Conclusao atual de {summary.get('completion_percentage', 0)}% com {done_points:.0f} ponto(s) concluidos e {remaining:.2f} sprint(s) ainda projetadas para concluir a release.",
        ]
        if delay > 0 and cost_variance > 0:
            lines.append(
                f"O projeto combina atraso de {delay:.2f} sprint(s) com desvio de custo de {self._format_currency(cost_variance)} acima do BAC."
            )
            lines.append("Decisao sugerida: revisar escopo imediato, capacidade da squad e horas extras antes da proxima sprint.")
        elif delay > 0:
            lines.append(f"O principal risco atual e prazo: a entrega final projeta {delay:.2f} sprint(s) de atraso.")
            lines.append("Decisao sugerida: reduzir escopo, reforcar capacidade ou renegociar marcos de entrega.")
        elif cost_variance > 0:
            lines.append(f"O principal risco atual e custo: o EAC projeta {self._format_currency(cost_variance)} acima do BAC.")
            lines.append("Decisao sugerida: revisar alocacao, produtividade e ocorrencia de hora extra.")
        else:
            lines.append("O projeto segue controlado em custo e prazo com a tendencia atual.")
            lines.append("Decisao sugerida: preservar a cadencia e monitorar crescimento de escopo nas proximas sprints.")

        if scope_delta > 0:
            lines.append(f"Ha aumento de escopo de {scope_delta:.0f} ponto(s) versus a baseline, o que pressiona a previsao final.")
        return lines

    def _sprint_reading_summary(self, record):
        planned = float(record.get("plan_points", 0) or 0)
        done = float(record.get("done_points", 0) or 0)
        added = float(record.get("added_points", 0) or 0)
        ac = float(record.get("AC", 0) or 0)
        suggested = float(record.get("suggested_cost", 0) or 0)
        lines = [
            f"A sprint entregou {done:.0f} de {planned:.0f} ponto(s) planejados.",
            f"CPI {record.get('CPI', 0):.2f} e SPI {record.get('SPI', 0):.2f} mostram o desempenho especifico desta sprint.",
        ]
        if added > 0:
            lines.append(f"Foram adicionados {added:.0f} ponto(s) de escopo nesta sprint, elevando a pressao sobre as proximas entregas.")
        if suggested > 0 and ac > suggested:
            lines.append(f"O custo realizado superou o custo padrao da sprint em {self._format_currency(ac - suggested)}.")
        return lines

    def _sprint_project_impact_summary(self, record):
        project_cpi = float(record.get("project_cpi", 0) or 0)
        project_spi = float(record.get("project_spi", 0) or 0)
        completion = float(record.get("completion_percentage", 0) or 0)
        lines = [
            f"Apos esta sprint, o projeto chegou a {completion:.2f}% de conclusao acumulada.",
            f"O acumulado ficou em CPI {project_cpi:.2f} e SPI {project_spi:.2f}.",
        ]
        if project_cpi < 1 and project_spi < 1:
            lines.append("Impacto para decisao: custo e prazo se deterioraram juntos; priorize replanejamento imediato.")
        elif project_spi < 1:
            lines.append("Impacto para decisao: o projeto perdeu ritmo; valide corte de escopo ou aumento de capacidade.")
        elif project_cpi < 1:
            lines.append("Impacto para decisao: o custo acumulado pressiona o BAC; revise hora extra e produtividade.")
        else:
            lines.append("Impacto para decisao: a sprint manteve o projeto sob controle acumulado.")
        return lines

    def _build_project_summary_page(self, summary):
        projection = summary.get("projection") or {}
        baseline = summary.get("baseline") or {}
        risk_level = self._project_risk_level(summary)
        fig, ax = self._new_canvas(
            "Relatorio Executivo do Projeto",
            "Panorama consolidado de custo, prazo, escopo e historico da release",
        )

        self._draw_info_band(
            ax,
            [
                ("Squad", summary.get("name", "Squad")),
                ("Gerado em", datetime.now().strftime("%d/%m/%Y %H:%M")),
                ("Baseline", "Ativa" if baseline else "Nao gerada"),
            ],
        )

        self._draw_risk_panel(
            ax,
            0.04,
            0.65,
            0.42,
            0.14,
            "Semaforo do projeto",
            risk_level,
            f"Status: {summary.get('status', '-')}",
        )
        self._draw_metric_card(ax, 0.50, 0.65, 0.20, 0.14, "Conclusao atual", f"{summary.get('completion_percentage', 0)}%", tone=risk_level)
        self._draw_metric_card(ax, 0.74, 0.65, 0.22, 0.14, "Custo da Squad", self._format_currency(summary.get("squad_cost", 0)))

        self._draw_metric_card(ax, 0.04, 0.51, 0.28, 0.11, "BAC atual", self._format_currency(summary.get("bac", 0)))
        self._draw_metric_card(
            ax,
            0.36,
            0.51,
            0.28,
            0.11,
            "Projecao de custo",
            self._format_currency(projection.get("eac", 0)),
            tone=risk_level,
        )
        self._draw_metric_card(
            ax,
            0.68,
            0.51,
            0.28,
            0.11,
            "Projecao de prazo",
            f"{projection.get('projected_total_sprints', 0):.2f} sprints",
            tone=risk_level,
        )

        self._draw_metric_card(ax, 0.04, 0.37, 0.28, 0.11, "Pontos da release", f"{summary.get('total_points', 0)}")
        self._draw_metric_card(
            ax,
            0.36,
            0.37,
            0.28,
            0.11,
            "Pontos concluidos",
            f"{sum(float(item.get('done_points', 0) or 0) for item in summary.get('history', [])):.0f}",
        )
        self._draw_metric_card(ax, 0.68, 0.37, 0.28, 0.11, "Sprints planejadas", f"{summary.get('total_sprints', 0)}")

        self._draw_text_box(
            ax,
            0.04,
            0.12,
            0.44,
            0.18,
            "Leitura executiva",
            self._project_executive_summary(summary),
            width=45,
        )
        baseline_lines = [
            f"BAC baseline: {self._format_currency(baseline.get('bac', 0))}" if baseline else "BAC baseline: -",
            f"Escopo baseline: {baseline.get('total_points', 0)}" if baseline else "Escopo baseline: -",
            f"Prazo baseline: {baseline.get('total_sprints', 0)} sprint(s)" if baseline else "Prazo baseline: -",
        ]
        self._draw_text_box(ax, 0.52, 0.12, 0.44, 0.18, "Contexto de baseline", baseline_lines, width=45)
        return fig

    def _build_project_insights_page(self, summary):
        projection = summary.get("projection") or {}
        baseline_comparison = summary.get("baseline_comparison") or {}
        fig, ax = self._new_canvas(
            "Leitura de Governanca",
            "Principais desvios e sinais para decisao executiva",
        )

        self._draw_info_band(
            ax,
            [
                ("Variacao de custo", self._format_currency(projection.get("cost_variance_at_completion", 0))),
                ("Atraso projetado", f"{projection.get('delay_sprints', 0):.2f} sprint(s)"),
                ("Sprints restantes", f"{projection.get('projected_remaining_sprints', 0):.2f}"),
            ],
        )

        self._draw_text_box(
            ax,
            0.04,
            0.56,
            0.43,
            0.22,
            "Leitura de decisao",
            [
                "Observe simultaneamente custo projetado, prazo projetado e escopo atual.",
                "Quando escopo cresce sem ganho proporcional de velocidade, a previsao de entrega piora.",
                "Use o semaforo para orientar a prioridade de acao executiva.",
            ],
            width=40,
        )
        self._draw_text_box(
            ax,
            0.52,
            0.56,
            0.44,
            0.22,
            "Comparativo com baseline",
            [
                f"Variacao de escopo: {baseline_comparison.get('scope_delta', 0)}",
                f"Variacao de prazo: {baseline_comparison.get('sprints_delta', 0)} sprint(s)",
                f"Variacao de custo da squad: {self._format_currency(baseline_comparison.get('squad_cost_delta', 0))}",
                f"Variacao de BAC: {self._format_currency(baseline_comparison.get('bac_delta', 0))}",
            ],
            width=40,
        )
        self._draw_text_box(
            ax,
            0.04,
            0.24,
            0.92,
            0.24,
            "Mensagem executiva",
            [
                "Se o custo final projetado subir acima do BAC, revise alocacao, capacidade e horas extras.",
                "Se o prazo projetado exceder o plano, renegocie escopo ou replaneje a cadencia de entrega.",
                "As paginas de sprint deste relatorio ajudam a localizar quando os desvios passaram a crescer.",
            ],
            width=92,
        )
        return fig

    def _build_sprint_evolution_pages(self, summary):
        pages = []
        history = summary.get("history", [])
        squad_name = summary.get("name", "Squad")

        for record in reversed(history):
            risk_level = self._sprint_risk_level(record)
            fig, ax = self._new_canvas(
                f"Evolucao da Sprint #{record.get('sprint_no', '-')}",
                "Detalhamento cumulativo da execucao da release",
            )
            self._draw_info_band(
                ax,
                [
                    ("Squad", squad_name),
                    ("Sprint", f"#{record.get('sprint_no', '-')}"),
                    ("Status acumulado", record.get("status", "-")),
                ],
            )

            self._draw_risk_panel(
                ax,
                0.04,
                0.65,
                0.42,
                0.14,
                "Semaforo da sprint",
                risk_level,
                f"Status: {record.get('sprint_status', record.get('status', '-'))}",
            )
            self._draw_metric_card(ax, 0.50, 0.65, 0.20, 0.14, "Conclusao acumulada", f"{record.get('completion_percentage', 0)}%", tone=risk_level)
            self._draw_metric_card(ax, 0.74, 0.65, 0.22, 0.14, "Status do projeto", record.get("status", "-"), tone=risk_level)

            self._draw_metric_card(ax, 0.04, 0.51, 0.28, 0.11, "PV da sprint", self._format_currency(record.get("PV", 0)))
            self._draw_metric_card(ax, 0.36, 0.51, 0.28, 0.11, "EV da sprint", self._format_currency(record.get("EV", 0)))
            self._draw_metric_card(ax, 0.68, 0.51, 0.28, 0.11, "AC da sprint", self._format_currency(record.get("AC", 0)))

            cpi_tone = "green" if float(record.get("CPI", 0) or 0) >= 1 else "red"
            spi_tone = "green" if float(record.get("SPI", 0) or 0) >= 1 else "red"
            self._draw_metric_card(ax, 0.04, 0.37, 0.28, 0.11, "CPI", f"{record.get('CPI', 0):.2f}", tone=cpi_tone)
            self._draw_metric_card(ax, 0.36, 0.37, 0.28, 0.11, "SPI", f"{record.get('SPI', 0):.2f}", tone=spi_tone)
            self._draw_metric_card(ax, 0.68, 0.37, 0.28, 0.11, "Pontos adicionados", f"{record.get('added_points', 0)}")

            self._draw_text_box(
                ax,
                0.04,
                0.12,
                0.44,
                0.18,
                "Leitura da sprint",
                self._sprint_reading_summary(record),
                width=42,
            )
            self._draw_text_box(
                ax,
                0.52,
                0.12,
                0.44,
                0.18,
                "Impacto no projeto",
                self._sprint_project_impact_summary(record),
                width=42,
            )
            pages.append(fig)
        return pages
