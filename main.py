import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class EVMApp:
    def __init__(self, root):
        self.root = root
        root.title("EVM Project (Python)")
        root.geometry("1000x700")

        self.value_per_point = tk.DoubleVar(value=100.0)
        self.total_sprints = tk.IntVar(value=6)
        self.sprint_weeks = tk.DoubleVar(value=2.0)
        self.plan_points_release = tk.DoubleVar(value=180)
        self.plan_points_sprint = tk.DoubleVar(value=30)

        self.team_role = tk.StringVar()
        self.team_salary = tk.DoubleVar(value=0.0)
        self.team_hourly_rate = tk.DoubleVar(value=0.0)
        self.team_function = tk.StringVar()
        self.team_members = []
        self.squad_cost_total = 0.0

        self.current_sprint = tk.IntVar(value=1)

        self.cum_sprint_no = []
        self.cum_PV = []
        self.cum_AC = []
        self.cum_EV = []

        self.setup_ui()

    def setup_ui(self):
        team_frame = ttk.LabelFrame(self.root, text="Configuração de custo da squad")
        team_frame.pack(fill="x", padx=10, pady=8)

        ttk.Label(team_frame, text="Cargo:").grid(row=0, column=0, sticky="e", padx=4, pady=2)
        ttk.Entry(team_frame, textvariable=self.team_role, width=14).grid(row=0, column=1, padx=4, pady=2)

        ttk.Label(team_frame, text="Salário base:").grid(row=0, column=2, sticky="e", padx=4, pady=2)
        ttk.Entry(team_frame, textvariable=self.team_salary, width=12).grid(row=0, column=3, padx=4, pady=2)

        ttk.Label(team_frame, text="Valor/hora:").grid(row=0, column=4, sticky="e", padx=4, pady=2)
        ttk.Entry(team_frame, textvariable=self.team_hourly_rate, width=12).grid(row=0, column=5, padx=4, pady=2)

        ttk.Label(team_frame, text="Função:").grid(row=1, column=0, sticky="e", padx=4, pady=2)
        ttk.Entry(team_frame, textvariable=self.team_function, width=14).grid(row=1, column=1, padx=4, pady=2)

        ttk.Button(team_frame, text="Adicionar membro", command=self.add_team_member).grid(row=1, column=3, padx=4, pady=2)

        self.team_table = ttk.Treeview(team_frame, columns=("role", "salary", "hourly", "function"), show="headings", height=4)
        self.team_table.heading("role", text="Cargo")
        self.team_table.heading("salary", text="Salário")
        self.team_table.heading("hourly", text="Valor/hora")
        self.team_table.heading("function", text="Função")
        self.team_table.grid(row=2, column=0, columnspan=6, padx=4, pady=4, sticky="nsew")

        self.team_cost_display = tk.StringVar(value="Custo total squad: 0.00")
        ttk.Label(team_frame, textvariable=self.team_cost_display, font=(None, 10, "bold")).grid(row=3, column=0, columnspan=3, sticky="w", padx=4, pady=2)

        plan_frame = ttk.LabelFrame(self.root, text="Planejamento de projeto")
        plan_frame.pack(fill="x", padx=10, pady=8)

        row = 0
        ttk.Label(plan_frame, text="Valor por ponto:").grid(row=row, column=0, sticky="e", padx=4, pady=2)
        ttk.Entry(plan_frame, textvariable=self.value_per_point, width=12).grid(row=row, column=1, padx=4, pady=2)

        ttk.Label(plan_frame, text="Sprints planejadas:").grid(row=row, column=2, sticky="e", padx=4, pady=2)
        ttk.Entry(plan_frame, textvariable=self.total_sprints, width=12).grid(row=row, column=3, padx=4, pady=2)

        row += 1
        ttk.Label(plan_frame, text="Duração da sprint (semanas):").grid(row=row, column=0, sticky="e", padx=4, pady=2)
        ttk.Entry(plan_frame, textvariable=self.sprint_weeks, width=12).grid(row=row, column=1, padx=4, pady=2)

        ttk.Label(plan_frame, text="Pontos planejados por release:").grid(row=row, column=2, sticky="e", padx=4, pady=2)
        ttk.Entry(plan_frame, textvariable=self.plan_points_release, width=12).grid(row=row, column=3, padx=4, pady=2)

        row += 1
        ttk.Label(plan_frame, text="Pontos planejados por sprint:").grid(row=row, column=0, sticky="e", padx=4, pady=2)
        ttk.Entry(plan_frame, textvariable=self.plan_points_sprint, width=12).grid(row=row, column=1, padx=4, pady=2)

        ttk.Button(plan_frame, text="Aplicar plano", command=self.apply_plan).grid(row=row, column=3, padx=4, pady=4)

        self.out_info = tk.StringVar(value="BAC: 0 | PV (cumulativo): 0 | PPC: 0%")
        ttk.Label(plan_frame, textvariable=self.out_info, font=(None, 10, "bold")).grid(row=2, column=4, sticky="w", padx=12)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tab1 = ttk.Frame(notebook)
        tab2 = ttk.Frame(notebook)

        notebook.add(tab1, text="Sprint & Cálculos")
        notebook.add(tab2, text="Gráfico Cumulativo")

        self.setup_tab1(tab1)
        self.setup_tab2(tab2)

        self.apply_plan()

    def setup_tab1(self, frame):
        input_frame = ttk.LabelFrame(frame, text="Entrada de Sprint")
        input_frame.pack(fill="x", padx=10, pady=8)

        ttk.Label(input_frame, text="Sprint #: ").grid(row=0, column=0, sticky="e")
        ttk.Entry(input_frame, textvariable=self.current_sprint, width=6).grid(row=0, column=1, padx=4, pady=4)

        self.sprint_plan_points = tk.DoubleVar(value=0)
        self.sprint_done_points = tk.DoubleVar(value=0)
        self.sprint_added_points = tk.DoubleVar(value=0)
        self.sprint_actual_cost = tk.DoubleVar(value=0)

        ttk.Label(input_frame, text="Pontos planejados na sprint:").grid(row=1, column=0, sticky="e")
        ttk.Entry(input_frame, textvariable=self.sprint_plan_points, width=12).grid(row=1, column=1, padx=4, pady=2)

        ttk.Label(input_frame, text="Pontos concluídos:").grid(row=2, column=0, sticky="e")
        ttk.Entry(input_frame, textvariable=self.sprint_done_points, width=12).grid(row=2, column=1, padx=4, pady=2)

        ttk.Label(input_frame, text="Pontos adicionados (scope):").grid(row=3, column=0, sticky="e")
        ttk.Entry(input_frame, textvariable=self.sprint_added_points, width=12).grid(row=3, column=1, padx=4, pady=2)

        ttk.Label(input_frame, text="Custo real (AC) da sprint:").grid(row=4, column=0, sticky="e")
        ttk.Entry(input_frame, textvariable=self.sprint_actual_cost, width=12).grid(row=4, column=1, padx=4, pady=2)

        ttk.Button(input_frame, text="Adicionar sprint", command=self.add_sprint).grid(row=5, column=1, pady=6)

        result_frame = ttk.LabelFrame(frame, text="Resultados da Sprint")
        result_frame.pack(fill="x", padx=10, pady=8)

        self.labels = {}
        for i, name in enumerate(["PV", "AC", "EV", "CV", "SV", "CPI", "SPI", "Status"]):
            ttk.Label(result_frame, text=f"{name}:").grid(row=i, column=0, sticky="e", padx=4, pady=2)
            self.labels[name] = ttk.Label(result_frame, text="0")
            self.labels[name].grid(row=i, column=1, sticky="w", padx=4, pady=2)

        self.history_text = tk.Text(frame, height=8)
        self.history_text.pack(fill="both", padx=10, pady=8, expand=False)
        self.history_text.insert("end", "Histórico de sprints:\n")
        self.history_text.configure(state="disabled")

    def setup_tab2(self, frame):
        fig = Figure(figsize=(10, 5), dpi=100)
        self.ax = fig.add_subplot(111)
        self.ax.set_title("Cumulação de PV/AC/EV por Sprint")
        self.ax.set_xlabel("Sprint")
        self.ax.set_ylabel("Valor")

        self.canvas = FigureCanvasTkAgg(fig, master=frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def add_team_member(self):
        role = self.team_role.get().strip()
        function = self.team_function.get().strip()
        salary = self.team_salary.get()
        hourly = self.team_hourly_rate.get()

        if not role or not function:
            messagebox.showerror("Erro", "Cargo e função são obrigatórios")
            return

        if salary < 0 or hourly < 0:
            messagebox.showerror("Erro", "Salário e valor/hora não podem ser negativos")
            return

        self.team_members.append({
            "role": role,
            "function": function,
            "salary": salary,
            "hourly": hourly,
        })

        self.team_table.insert("", "end", values=(role, f"{salary:.2f}", f"{hourly:.2f}", function))

        self.team_role.set("")
        self.team_function.set("")
        self.team_salary.set(0.0)
        self.team_hourly_rate.set(0.0)

        self.update_team_cost()

    def update_team_cost(self):
        total = 0.0
        for member in self.team_members:
            # Estimativa simples: custo é salário + 160h * valor/hora, ajuste conforme necessidade
            total += member["salary"] + member["hourly"] * 160

        self.squad_cost_total = total
        self.team_cost_display.set(f"Custo total squad: {total:.2f}")

        points_release = self.plan_points_release.get()
        if points_release > 0:
            self.value_per_point.set(total / points_release)

        self.apply_plan()

    def apply_plan(self):
        try:
            value_per_point = self.value_per_point.get()
            total_points = self.plan_points_release.get()
            total_sprints = self.total_sprints.get()
            if total_sprints <= 0:
                raise ValueError("Sprints deve ser maior que 0")

            bac = total_points * value_per_point
            planned_total_points = self.plan_points_sprint.get() * total_sprints
            self.bac = bac
            self.pv_total = planned_total_points * value_per_point

            self.update_project_info()

        except Exception as e:
            messagebox.showerror("Erro de plano", str(e))

    def update_project_info(self):
        plan_points = self.plan_points_sprint.get() * self.total_sprints.get()
        done_points = sum(self.cum_EV) / self.value_per_point.get() if self.cum_EV else 0
        ppc = (done_points / plan_points * 100) if plan_points > 0 else 0

        self.out_info.set(
            f"BAC: {self.bac:.2f} | PV (Total planejado): {self.pv_total:.2f} | PPC: {ppc:.2f}%"
        )

    def add_sprint(self):
        try:
            sprint_no = self.current_sprint.get()
            plan = self.sprint_plan_points.get()
            done = self.sprint_done_points.get()
            added = self.sprint_added_points.get()
            ac = self.sprint_actual_cost.get()

            if plan < 0 or done < 0 or added < 0 or ac < 0:
                raise ValueError("Números negativos não são permitidos")

            value = self.value_per_point.get()

            pv = plan * value
            ev = done * value
            ac_value = ac

            cv = ev - ac_value
            sv = ev - pv
            cpi = ev / ac_value if ac_value > 0 else 0
            spi = ev / pv if pv > 0 else 0

            self.cum_sprint_no.append(sprint_no)
            self.cum_PV.append(pv + (self.cum_PV[-1] if self.cum_PV else 0))
            self.cum_AC.append(ac_value + (self.cum_AC[-1] if self.cum_AC else 0))
            self.cum_EV.append(ev + (self.cum_EV[-1] if self.cum_EV else 0))

            self.labels["PV"].config(text=f"{pv:.2f}")
            self.labels["AC"].config(text=f"{ac_value:.2f}")
            self.labels["EV"].config(text=f"{ev:.2f}")
            self.labels["CV"].config(text=f"{cv:.2f}")
            self.labels["SV"].config(text=f"{sv:.2f}")
            self.labels["CPI"].config(text=f"{cpi:.2f}")
            self.labels["SPI"].config(text=f"{spi:.2f}")

            status = "OK"
            if cpi < 1 or spi < 1:
                status = "Atenção: Fora do planejado"
            self.labels["Status"].config(text=status)

            self.history_text.configure(state="normal")
            self.history_text.insert("end", f"Sprint {sprint_no}: Plan={plan}, Done={done}, Added={added}, AC={ac_value}, PV={pv:.2f}, EV={ev:.2f}, CV={cv:.2f}, SV={sv:.2f}, CPI={cpi:.2f}, SPI={spi:.2f}\n")
            self.history_text.configure(state="disabled")

            self.current_sprint.set(sprint_no + 1)
            self.plot_chart()
            self.update_project_info()

        except Exception as e:
            messagebox.showerror("Erro de sprint", str(e))

    def plot_chart(self):
        self.ax.cla()
        self.ax.plot(self.cum_sprint_no, self.cum_PV, marker='o', label='PV Cumulativo')
        self.ax.plot(self.cum_sprint_no, self.cum_AC, marker='o', label='AC Cumulativo')
        self.ax.plot(self.cum_sprint_no, self.cum_EV, marker='o', label='EV Cumulativo')
        self.ax.set_title("Cumulação de PV/AC/EV por Sprint")
        self.ax.set_xlabel("Sprint")
        self.ax.set_ylabel("Valor")
        self.ax.legend()
        self.ax.grid(True)
        self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app = EVMApp(root)
    root.mainloop()
