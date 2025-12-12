import tkinter as tk
from tkinter import ttk, messagebox
import datetime
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from interfaces import IView
from models import Anomaly

# Диалог подтверждения аномалии
class AnomalyConfirmationDialog:
    def __init__(self, app, anomaly: Anomaly):
        self.app = app
        self.anomaly = anomaly
        alerts = self.app.alert_service.get_alerts()
        self.alert = next((al for al in alerts if al.anomaly_id == anomaly.anomaly_id), None)
        
        if self.alert is None:
            self.app.alert_service.send_alert(anomaly, self.app.current_user)
            alerts = self.app.alert_service.get_alerts()
            self.alert = next((al for al in alerts if al.anomaly_id == anomaly.anomaly_id), None)
        
        self.win = tk.Toplevel(self.app)
        self.win.title("Anomaly Details")
        self.win.configure(bg='#001f3f')
        self.build_ui()

    def build_ui(self):
        a = self.anomaly
        tk.Label(self.win, text=f"ID: {a.anomaly_id}", bg='#001f3f', fg="white").pack(anchor='w', padx=10, pady=2)
        tk.Label(self.win, text=f"Data ID: {a.data_id}", bg='#001f3f', fg="white").pack(anchor='w', padx=10, pady=2)
        tk.Label(self.win, text=f"Detection Time: {a.detection_time}", bg='#001f3f', fg="white").pack(anchor='w', padx=10, pady=2)
        tk.Label(self.win, text=f"Score: {a.score}", bg='#001f3f', fg="white").pack(anchor='w', padx=10, pady=2)
        tk.Label(self.win, text=f"Description: {a.description}", bg='#001f3f', fg="white", 
                wraplength=500, justify='left').pack(anchor='w', padx=10, pady=2)
        tk.Label(self.win, text=f"Severity: {a.severity}", bg='#001f3f', fg="white").pack(anchor='w', padx=10, pady=6)
        
        status_text = self.alert.status if self.alert is not None else "no alert"
        self.status_label = tk.Label(self.win, text=f"Alert status: {status_text}", 
                                    bg='#001f3f', fg="white")
        self.status_label.pack(padx=10, pady=4)
        
        btn_frame = tk.Frame(self.win, bg='#001f3f')
        btn_frame.pack(pady=8, padx=10, fill='x')
        
        confirm_btn = ttk.Button(btn_frame, text="Confirm", command=self.confirm)
        confirm_btn.pack(side=tk.LEFT, expand=True, fill='x', padx=5)
        
        false_btn = ttk.Button(btn_frame, text="False Positive", command=self.false_positive)
        false_btn.pack(side=tk.LEFT, expand=True, fill='x', padx=5)
        
        close_btn = ttk.Button(btn_frame, text="Close", command=self.win.destroy)
        close_btn.pack(side=tk.LEFT, expand=True, fill='x', padx=5)
        
        if self.alert and self.alert.status == 'confirmed':
            confirm_btn.state(['disabled'])
            self.status_label.config(text=f"Alert status: {self.alert.status}")

    def confirm(self):
        if self.alert is None:
            self.app.alert_service.send_alert(self.anomaly, self.app.current_user)
            alerts = self.app.alert_service.get_alerts()
            self.alert = next((al for al in alerts if al.anomaly_id == self.anomaly.anomaly_id), None)
        
        if self.alert:
            self.app.alert_service.update_alert_status(self.alert.alert_id, 'confirmed')
            self.status_label.config(text=f"Alert status: confirmed")
            messagebox.showinfo("Confirmed", "Anomaly confirmed.")
            if self.app.current_view in ['Alerts', 'Historical Analysis', 'Dashboard']:
                self.app.switch_view(self.app.current_view)
            self.win.destroy()

    def false_positive(self):
        if self.alert is None:
            self.app.alert_service.send_alert(self.anomaly, self.app.current_user)
            alerts = self.app.alert_service.get_alerts()
            self.alert = next((al for al in alerts if al.anomaly_id == self.anomaly.anomaly_id), None)
        
        if self.alert:
            self.app.alert_service.update_alert_status(self.alert.alert_id, 'false_positive')
            try:
                self.app.trigger_retraining()
            except Exception:
                pass
            messagebox.showinfo("Marked", "Anomaly marked as false positive.")
            if self.app.current_view in ['Alerts', 'Historical Analysis', 'Dashboard']:
                self.app.switch_view(self.app.current_view)
            self.win.destroy()

# Основное представление дашборда
class MainMonitorView(IView):
    def __init__(self, app):
        self.app = app
        self.canvas = None
        self.ax = None
        self.anomaly_list = None
        self.canvas2 = None
        self.ax2 = None
        self.update_id = None

    def render(self):
        tk.Label(self.app.content, text="Dashboard - Current Anomalies", 
                font=("Arial", 16), bg="#001f3f", fg="white").pack(pady=10)
        self.update_graphs()

    def stop_update(self):
        if self.update_id:
            self.app.after_cancel(self.update_id)
            self.update_id = None

    def update_graphs(self):
        if self.app.current_view != self.get_view_name():
            return
        
        # Проверка и сброс виджетов при необходимости
        try:
            if getattr(self, 'anomaly_list', None) is not None:
                if not self.anomaly_list.winfo_exists():
                    self._reset_widgets()
        except tk.TclError:
            self._reset_widgets()
        
        # Создание виджетов графиков если нужно
        if not self.canvas:
            self._create_widgets()
        
        # Обновление данных и графиков
        self._update_data_and_charts()
        
        # Планирование следующего обновления
        self.update_id = self.app.after(1000, self.update_graphs)

    def _reset_widgets(self):
        """Сброс виджетов"""
        self.canvas = None
        self.canvas2 = None
        self.anomaly_list = None
        self.ax = None
        self.ax2 = None

    def _create_widgets(self):
        """Создание виджетов графиков"""
        self.fig = Figure(figsize=(6, 4), dpi=100, facecolor='#001f3f')
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.app.content)
        self.canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        if self.app.role == 'security':
            self.fig2 = Figure(figsize=(6, 4), dpi=100, facecolor='#001f3f')
            self.ax2 = self.fig2.add_subplot(111)
            self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.app.content)
            self.canvas2.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        list_frame = tk.Frame(self.app.content, bg='#001f3f')
        list_frame.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Label(list_frame, text="Anomalies", font=("Arial", 12), 
                bg='#001f3f', fg="white").pack()
        self.anomaly_list = tk.Listbox(list_frame, height=20, width=50, 
                                      bg='#0a192f', fg="white", selectbackground="cyan")
        self.anomaly_list.pack()

    def _update_data_and_charts(self):
        """Обновление данных и графиков"""
        historical_data = self.app.data_storage.get_historical_data(
            datetime.datetime.min, datetime.datetime.max
        )
        filtered_data = [d for d in historical_data if self.app.filter_by_role(d.data_type)]
        
        if not filtered_data:
            return
        
        # Агрегация данных по дням
        daily_features = defaultdict(list)
        for d in filtered_data:
            day = d.timestamp.date()
            daily_features[day].append(d.features[0])
        
        daily_times = sorted(daily_features.keys())
        daily_avg = [sum(daily_features[day]) / len(daily_features[day]) for day in daily_times]
        
        # Получение аномалий
        anomalies = self.app.data_storage.get_anomalies(self.app.role)
        daily_anomaly_scores = defaultdict(list)
        for a in anomalies:
            day = a.detection_time.date()
            daily_anomaly_scores[day].append(a.score)
        
        daily_anomaly_avg = [
            (sum(daily_anomaly_scores.get(day, [0])) / len(daily_anomaly_scores.get(day, [1]))) 
            if daily_anomaly_scores.get(day) else None 
            for day in daily_times
        ]
        
        # Отрисовка основного графика
        if self.ax:
            self.ax.clear()
            self.ax.plot(daily_times, daily_avg, label='Avg Feature', color='cyan')
            anomaly_days = [day for i, day in enumerate(daily_times) if daily_anomaly_avg[i] is not None]
            anomaly_values = [val for val in daily_anomaly_avg if val is not None]
            if anomaly_days:
                self.ax.scatter(anomaly_days, anomaly_values, color='red', label='Avg Anomaly Score')
            
            self.ax.set_xlabel("Day")
            self.ax.set_ylabel("Value")
            self.ax.set_facecolor('#001f3f')
            self.ax.tick_params(colors='white')
            
            for spine in ['bottom', 'top', 'left', 'right']:
                self.ax.spines[spine].set_color('white')
            
            # Заголовок в зависимости от роли
            titles = {
                'equipment': 'Daily Avg Temperature',
                'fraud': 'Daily Avg Transaction Time',
                'security': 'Daily Avg Traffic Volume'
            }
            self.ax.set_title(titles.get(self.app.role, ''), color='white')
            self.ax.legend()
            plt.setp(self.ax.get_xticklabels(), rotation=45, ha="right", color='white')
            self.canvas.draw()
        
        # Дополнительный график для security
        if self.app.role == 'security' and getattr(self, 'ax2', None):
            self.ax2.clear()
            ips = [
                raw.attributes.get('ip') for raw in self.app.data_storage.raw_data 
                if raw.attributes.get('type') == '3' and 'ip' in raw.attributes
            ]
            ip_counts = Counter(ips)
            top_ips = list(ip_counts.items())[:10]
            
            if top_ips:
                keys, vals = zip(*top_ips)
                self.ax2.bar(list(keys), list(vals), color='cyan')
                self.ax2.set_title('IP Address Frequency', color='white')
                self.ax2.set_xlabel('IP')
                self.ax2.set_ylabel('Count')
                self.ax2.set_facecolor('#001f3f')
                self.ax2.tick_params(colors='white')
                
                for spine in ['bottom', 'top', 'left', 'right']:
                    self.ax2.spines[spine].set_color('white')
                
                plt.setp(self.ax2.get_xticklabels(), rotation=45, ha="right", color='white')
                self.canvas2.draw()
        
        # Обновление списка аномалий
        try:
            if getattr(self, 'anomaly_list', None) is not None and self.anomaly_list.winfo_exists():
                self.anomaly_list.delete(0, tk.END)
                for a in anomalies:
                    self.anomaly_list.insert(tk.END, f"{a.description} - Score: {a.score}")
        except tk.TclError:
            self._reset_widgets()

    def handle_input(self):
        """Обработка ввода пользователя"""
        try:
            if getattr(self, 'anomaly_list', None) is not None and self.anomaly_list.winfo_exists():
                try:
                    self.anomaly_list.unbind('<<ListboxSelect>>')
                except Exception:
                    pass
                
                self.anomaly_list.bind('<<ListboxSelect>>', self.show_anomaly_details)
                
                try:
                    self.anomaly_list.unbind('<Double-1>')
                except Exception:
                    pass
                self.anomaly_list.bind('<Double-1>', lambda e: self.show_anomaly_details(e))
        except tk.TclError:
            pass

    def show_anomaly_details(self, event):
        """Показать детали аномалии"""
        selection = self.anomaly_list.curselection()
        if selection:
            index = selection[0]
            anomalies = self.app.data_storage.get_anomalies(self.app.role)
            if index < len(anomalies):
                a = anomalies[index]
                AnomalyConfirmationDialog(self.app, a)

    def get_view_name(self) -> str:
        return "Dashboard"

# Представление исторического анализа
class HistoricalView(IView):
    def __init__(self, app):
        self.app = app
        self.start_time = datetime.datetime.min
        self.end_time = datetime.datetime.max
        self.canvas = None
        self.ax = None
        self.update_id = None
        self.filter_frame = None

    def render(self):
        tk.Label(self.app.content, text="Historical Analysis", 
                font=("Arial", 16), bg="#001f3f", fg="white").pack(pady=10)
        
        # Фильтры дат
        self.filter_frame = ttk.Frame(self.app.content)
        self.filter_frame.pack(pady=10)
        
        ttk.Label(self.filter_frame, text="Start Date (YYYY-MM-DD):").pack(side=tk.LEFT)
        self.hist_start_date_entry = ttk.Entry(self.filter_frame)
        self.hist_start_date_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(self.filter_frame, text="End Date (YYYY-MM-DD):").pack(side=tk.LEFT)
        self.hist_end_date_entry = ttk.Entry(self.filter_frame)
        self.hist_end_date_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(self.filter_frame, text="Filter", command=self.apply_filter).pack(side=tk.LEFT, padx=5)
        
        self.update_graphs()

    def stop_update(self):
        if self.update_id:
            self.app.after_cancel(self.update_id)
            self.update_id = None

    def update_graphs(self):
        if self.app.current_view != self.get_view_name():
            return
        
        # Проверка canvas
        try:
            if getattr(self, 'canvas', None) is not None:
                if not self.canvas.get_tk_widget().winfo_exists():
                    self.canvas = None
                    self.ax = None
        except tk.TclError:
            self.canvas = None
            self.ax = None
        
        # Получение данных
        all_anomalies = self.app.anomaly_controller.get_anomalies_in_period(
            self.start_time, self.end_time, self.app.role
        )
        
        confirmed_ids = set()
        for al in self.app.alert_service.get_alerts():
            if al.status == 'confirmed':
                confirmed_ids.add(al.anomaly_id)
        
        anomalies = [a for a in all_anomalies if a.anomaly_id in confirmed_ids]
        
        # Создание графиков
        if not getattr(self, 'canvas', None):
            self.fig = Figure(figsize=(10, 5), dpi=100, facecolor='#001f3f')
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.app.content)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Отрисовка графика
        self.ax.clear()
        if anomalies:
            daily_counts = defaultdict(int)
            for a in anomalies:
                day = a.detection_time.date()
                daily_counts[day] += 1
            
            daily_times = sorted(daily_counts.keys())
            counts = [daily_counts[day] for day in daily_times]
            self.ax.bar(daily_times, counts)
            self.ax.set_title('Daily Confirmed Anomaly Counts', color='white')
        else:
            self.ax.text(0.5, 0.5, "No confirmed anomalies in the selected range", 
                        ha='center', va='center', transform=self.ax.transAxes, color='white')
            self.ax.set_title('Daily Confirmed Anomaly Counts', color='white')
        
        self.ax.set_xlabel("Day")
        self.ax.set_ylabel("Count")
        self.ax.set_facecolor('#001f3f')
        self.ax.tick_params(colors='white')
        
        for spine in ['bottom', 'top', 'left', 'right']:
            self.ax.spines[spine].set_color('white')
        
        plt.setp(self.ax.get_xticklabels(), rotation=45, ha="right", color='white')
        self.canvas.draw()
        
        # Список аномалий
        if not hasattr(self, 'results_frame') or not getattr(self, 'results_frame').winfo_exists():
            self.results_frame = tk.Frame(self.app.content, bg='#001f3f')
            self.results_frame.pack(fill=tk.X, pady=10)
        else:
            for w in self.results_frame.winfo_children():
                w.destroy()
        
        if anomalies:
            for a in anomalies:
                lbl = ttk.Label(self.results_frame, text=f"{a.description} at {a.detection_time}")
                lbl.pack(anchor='w', pady=2, padx=5)
                lbl.bind("<Button-1>", lambda e, anomaly=a: AnomalyConfirmationDialog(self.app, anomaly))
        else:
            ttk.Label(self.results_frame, text="No confirmed anomalies found for selected period.").pack(anchor='w')
        
        self.update_id = self.app.after(1000, self.update_graphs)

    def apply_filter(self):
        """Применить фильтр дат"""
        try:
            start_str = self.hist_start_date_entry.get()
            end_str = self.hist_end_date_entry.get()
            
            self.start_time = datetime.datetime.strptime(start_str, "%Y-%m-%d") if start_str else datetime.datetime.min
            self.end_time = datetime.datetime.strptime(end_str, "%Y-%m-%d") if end_str else datetime.datetime.max
            
            self.update_graphs()
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")

    def handle_input(self):
        pass

    def get_view_name(self) -> str:
        return "Historical Analysis"

# Представление оповещений
class AlertsView(IView):
    def __init__(self, app):
        self.app = app
        self.update_id = None

    def render(self):
        tk.Label(self.app.content, text="Alerts", 
                font=("Arial", 16), bg="#001f3f", fg="white").pack(pady=10)
        self.update_alerts()

    def stop_update(self):
        if self.update_id:
            self.app.after_cancel(self.update_id)
            self.update_id = None

    def update_alerts(self):
        if self.app.current_view != self.get_view_name():
            return
        
        # Очистка контента
        for widget in self.app.content.winfo_children()[1:]:
            widget.destroy()
        
        role_map = {
            'security': 'traffic',
            'equipment': 'sensor',
            'fraud': 'transaction'
        }
        allowed_type = role_map.get(self.app.role, '')
        
        # Сбор подтвержденных оповещений
        confirmed_alerts = []
        for al in self.app.alert_service.get_alerts():
            if al.status == 'confirmed':
                anomaly = self.app.data_storage.get_anomaly(al.anomaly_id)
                if anomaly and anomaly.description.startswith(allowed_type + ":"):
                    confirmed_alerts.append((al, anomaly))
        
        # Разделение на новые и старые
        last_visit = getattr(self.app, 'last_alerts_view_time', datetime.datetime.min)
        new_alerts = []
        old_alerts = []
        
        for al, anomaly in confirmed_alerts:
            conf_time = self.app.alert_service.confirmed_times.get(al.alert_id, al.time_raised)
            if conf_time > last_visit:
                new_alerts.append((al, anomaly))
            else:
                old_alerts.append((al, anomaly))
        
        # Отображение новых оповещений
        if new_alerts:
            header = ttk.Label(self.app.content, text=f"New Confirmed Alerts ({len(new_alerts)})",
                             font=("Arial", 12, "bold"), background='#001f3f', foreground='yellow')
            header.pack(fill=tk.X, pady=(5, 2))
            
            for al, anomaly in new_alerts:
                frame = ttk.Frame(self.app.content)
                frame.pack(fill=tk.X, pady=2, padx=5)
                
                new_badge = tk.Label(frame, text="NEW", bg='red', fg='white', padx=6)
                new_badge.pack(side=tk.LEFT, padx=(0, 6))
                
                ttk.Label(frame, text=al.message).pack(side=tk.LEFT, expand=True, fill=tk.X)
                
                ttk.Button(frame, text="Acknowledge",
                         command=lambda aid=al.alert_id: self.app.anomaly_controller.acknowledge_alert(aid)).pack(side=tk.RIGHT)
        
        # Отображение старых оповещений
        if old_alerts:
            header2 = ttk.Label(self.app.content, text="Confirmed Alerts", 
                              font=("Arial", 12, "bold"), background='#001f3f', foreground='white')
            header2.pack(fill=tk.X, pady=(10, 2))
            
            for al, anomaly in old_alerts:
                frame = ttk.Frame(self.app.content)
                frame.pack(fill=tk.X, pady=2, padx=5)
                
                ttk.Label(frame, text=al.message).pack(side=tk.LEFT, expand=True, fill=tk.X)
                
                ttk.Button(frame, text="Acknowledge",
                         command=lambda aid=al.alert_id: self.app.anomaly_controller.acknowledge_alert(aid)).pack(side=tk.RIGHT)
        
        # Сообщение если нет оповещений
        if not new_alerts and not old_alerts:
            ttk.Label(self.app.content, text="No confirmed alerts for your role.", 
                     background='#001f3f').pack(pady=10)
        
        # Обновление времени последнего посещения
        self.app.last_alerts_view_time = datetime.datetime.now()
        
        # Планирование следующего обновления
        self.update_id = self.app.after(1000, self.update_alerts)

    def handle_input(self):
        pass

    def get_view_name(self) -> str:
        return "Alerts"

# Представление настроек
class SettingsView(IView):
    def __init__(self, app):
        self.app = app
        self.sens_scale = None
        self.sens_label = None
        self.set_button = None
        self.tune_button = None

    def render(self):
        tk.Label(self.app.content, text="Settings", 
                font=("Arial", 16), bg="#001f3f", fg="white").pack(pady=10)
        
        settings = self.app.config_controller.get_settings_for_user(self.app.current_user.user_id)
        
        tk.Label(self.app.content, text="Sensitivity:", 
                font=("Arial", 12), bg="#001f3f", fg="white").pack()
        
        # Контейнер для центрирования
        center_container = tk.Frame(self.app.content, bg="#001f3f")
        center_container.pack(fill=tk.X, pady=10)
        
        sens_frame = tk.Frame(center_container, bg="#001f3f")
        sens_frame.pack(padx=150, fill=tk.X)
        
        self.sens_label = tk.Label(sens_frame, text=f"{settings.sensitivity:.2f}", 
                                  bg="#001f3f", fg="white")
        self.sens_label.pack(side=tk.LEFT, padx=10)
        
        self.sens_scale = ttk.Scale(sens_frame, from_=0.0, to=1.0, orient='horizontal',
                                   value=settings.sensitivity, length=600)
        self.sens_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        # Кнопки
        self.set_button = ttk.Button(self.app.content, text="Set Sensitivity")
        self.set_button.pack(pady=5)
        
        self.tune_button = ttk.Button(self.app.content, text="Tune Sensitivity")
        self.tune_button.pack(pady=5)

    def update_label(self, value):
        """Обновление метки чувствительности"""
        self.sens_label.config(text=f"{float(value):.2f}")

    def set_sensitivity(self):
        """Установка чувствительности"""
        s = self.sens_scale.get()
        settings = self.app.config_controller.get_settings_for_user(self.app.current_user.user_id)
        settings.sensitivity = s
        self.app.config_controller.save_user_settings(settings)
        self.app.anomaly_controller.update_global_sensitivity(s)
        messagebox.showinfo("Success", f"Sensitivity set to {s:.2f}")
        self.app.switch_view("Settings")

    def tune_sensitivity(self):
        """Настройка чувствительности"""
        self.app.trigger_retraining()
        messagebox.showinfo("Success", f"Tuned sensitivity to {self.app.detector.global_sensitivity:.2f}")
        self.app.switch_view("Settings")

    def handle_input(self):
        """Обработка ввода для виджетов настроек"""
        try:
            # Привязка слайдера
            if self.sens_scale is not None:
                try:
                    self.sens_scale.configure(command=lambda v: None)
                except Exception:
                    pass
                self.sens_scale.configure(command=self.update_label)
            
            # Привязка кнопок
            if self.set_button is not None:
                try:
                    self.set_button.configure(command=self.set_sensitivity)
                except Exception:
                    try:
                        self.set_button.bind("<Button-1>", lambda e: self.set_sensitivity())
                    except Exception:
                        pass
            
            if self.tune_button is not None:
                try:
                    self.tune_button.configure(command=self.tune_sensitivity)
                except Exception:
                    try:
                        self.tune_button.bind("<Button-1>", lambda e: self.tune_sensitivity())
                    except Exception:
                        pass
        except tk.TclError:
            pass

    def get_view_name(self) -> str:
        return "Settings"