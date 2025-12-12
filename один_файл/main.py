import datetime
import uuid
import random
import tkinter as tk
from tkinter import messagebox, ttk
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
import abc
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading
import time
from collections import Counter, defaultdict
import json
import os

# Data Models
@dataclass
class RawData:
    id: str
    timestamp: datetime.datetime
    source: str
    attributes: Dict[str, str]

@dataclass
class PreparedData:
    id: str
    timestamp: datetime.datetime
    data_type: str
    features: List[float]

@dataclass
class User:
    user_id: str
    username: str
    role: str
    email: str

@dataclass
class Anomaly:
    anomaly_id: str
    data_id: str
    detection_time: datetime.datetime
    score: float
    description: str
    severity: str

@dataclass
class Alert:
    alert_id: str
    anomaly_id: str
    time_raised: datetime.datetime
    message: str
    status: str

@dataclass
class DetectionSettings:
    user_id: str
    sensitivity: float  # 0.0 to 1.0
    monitored_sources: List[str]

# Interfaces (Abstract Classes in Python)
class ISettingsRepository(abc.ABC):
    @abc.abstractmethod
    def load_settings(self, user_id: str) -> DetectionSettings:
        pass

    @abc.abstractmethod
    def save_settings(self, settings: DetectionSettings):
        pass

class IAnomalyDetector(abc.ABC):
    @abc.abstractmethod
    def train_model(self, historical_data: List[PreparedData]):
        pass

    @abc.abstractmethod
    def detect(self, data: PreparedData, settings: DetectionSettings) -> Optional[Anomaly]:
        pass

    @abc.abstractmethod
    def set_global_sensitivity(self, sensitivity: float):
        pass

class IDataStorage(abc.ABC):
    @abc.abstractmethod
    def store_raw_data(self, data: RawData):
        pass

    @abc.abstractmethod
    def store_prepared_data(self, data: PreparedData):
        pass

    @abc.abstractmethod
    def get_historical_data(self, start_time: datetime.datetime, end_time: datetime.datetime) -> List[PreparedData]:
        pass

class IDataSource(abc.ABC):
    @abc.abstractmethod
    def connect(self) -> bool:
        pass

    @abc.abstractmethod
    def get_next_data_chunk(self) -> RawData:
        pass

    @abc.abstractmethod
    def register_data_listener(self, callback: Callable[[RawData], None]):
        pass

class IAlertService(abc.ABC):
    @abc.abstractmethod
    def send_alert(self, anomaly: Anomaly, user: User):
        pass

    @abc.abstractmethod
    def update_alert_status(self, alert_id: str, new_status: str):
        pass

class IView(abc.ABC):
    @abc.abstractmethod
    def render(self):
        pass

    @abc.abstractmethod
    def handle_input(self):
        pass

    @abc.abstractmethod
    def get_view_name(self) -> str:
        pass

    def stop_update(self):
        pass

# Implementations
class JsonSettingsRepository(ISettingsRepository):
    def __init__(self, file_path="settings.json"):
        self.file_path = file_path
        self.settings_dict = {}
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                self.settings_dict = json.load(f)

    def load_settings(self, user_id: str) -> DetectionSettings:
        data = self.settings_dict.get(user_id, {"sensitivity": 0.5, "monitored_sources": ["any"]})
        return DetectionSettings(user_id, data["sensitivity"], data["monitored_sources"])

    def save_settings(self, settings: DetectionSettings):
        self.settings_dict[settings.user_id] = {"sensitivity": settings.sensitivity, "monitored_sources": settings.monitored_sources}
        with open(self.file_path, 'w') as f:
            json.dump(self.settings_dict, f)

class SimpleAnomalyDetector(IAnomalyDetector):
    def __init__(self):
        self.global_sensitivity: float = 0.5

    def train_model(self, historical_data: List[PreparedData]):
        if not historical_data:
            return

        def count_anomalies(s: float) -> int:
            settings = DetectionSettings("default_user", s, ["any"])
            count = 0
            for data in historical_data:
                if self.detect(data, settings):
                    count += 1
            return count

        target = len(historical_data) // 2
        low, high = 0.0, 1.0
        for _ in range(20):  # Binary search
            mid = (low + high) / 2
            count = count_anomalies(mid)
            if count < target:
                high = mid
            else:
                low = mid
        self.set_global_sensitivity(low)

    def detect(self, data: PreparedData, settings: DetectionSettings) -> Optional[Anomaly]:
        s = settings.sensitivity if settings.sensitivity is not None else self.global_sensitivity
        if data.data_type == 'sensor':
            temp = data.features[0]
            threshold = (1.1 - s) * 150
            if temp > threshold:
                score = (temp / threshold) * 100
                desc = f"sensor: Temperature {temp} exceeds threshold {threshold}"
                severity = "high" if score > 150 else "medium"
                return Anomaly(str(uuid.uuid4()), data.id, data.timestamp, score, desc, severity)
        elif data.data_type == 'traffic':
            volume = data.features[0]
            threshold = (1.1 - s) * 1000
            if volume > threshold:
                score = (volume / threshold) * 100
                desc = f"traffic: Volume {volume} exceeds threshold {threshold}"
                severity = "high" if score > 150 else "medium"
                return Anomaly(str(uuid.uuid4()), data.id, data.timestamp, score, desc, severity)
        elif data.data_type == 'transaction':
            time_val = data.features[0]
            lower = s * 8.0
            upper = s * 22.0 + (1 - s * 2.0)
            score = 0.0
            desc = ""
            if time_val < lower:
                score = (lower / time_val) * 100 if time_val > 0 else 200.0
                desc = f"transaction: Time {time_val} below lower bound {lower}"
            elif time_val > upper:
                score = (time_val / upper) * 100
                desc = f"transaction: Time {time_val} above upper bound {upper}"
            if score > 100:
                severity = "high" if score > 150 else "medium"
                return Anomaly(str(uuid.uuid4()), data.id, data.timestamp, score, desc, severity)
        return None

    def set_global_sensitivity(self, sensitivity: float):
        self.global_sensitivity = sensitivity

class InMemoryDataStorage(IDataStorage):
    def __init__(self):
        self.raw_data: List[RawData] = []
        self.prepared_data: List[PreparedData] = []
        self.anomalies: List[Anomaly] = []  # Added for easy access

    def store_raw_data(self, data: RawData):
        self.raw_data.append(data)

    def store_prepared_data(self, data: PreparedData):
        self.prepared_data.append(data)

    def get_historical_data(self, start_time: datetime.datetime, end_time: datetime.datetime) -> List[PreparedData]:
        return [d for d in self.prepared_data if start_time <= d.timestamp <= end_time]

    def store_anomaly(self, anomaly: Anomaly):
        self.anomalies.append(anomaly)

    def get_anomalies(self, role: str, start_time: datetime.datetime = datetime.datetime.min, end_time: datetime.datetime = datetime.datetime.max) -> List[Anomaly]:
        role_map = {
            'security': 'traffic',
            'equipment': 'sensor',
            'fraud': 'transaction'
        }
        allowed_type = role_map.get(role, '')
        return [a for a in self.anomalies if a.description.startswith(allowed_type + ":") and start_time <= a.detection_time <= end_time]

    def get_anomaly(self, anomaly_id: str) -> Optional[Anomaly]:
        return next((a for a in self.anomalies if a.anomaly_id == anomaly_id), None)

class SimulatedDataSource(IDataSource):
    def __init__(self):
        self.listener: Optional[Callable[[RawData], None]] = None
        self.running = False
        self.current_timestamp = datetime.datetime(2025, 1, 1)
        self.generated_count = 0

    def connect(self) -> bool:
        self.running = True
        threading.Thread(target=self.generate_loop, daemon=True).start()
        return True

    def get_next_data_chunk(self) -> RawData:
        return self.generate_one_data()

    def register_data_listener(self, callback: Callable[[RawData], None]):
        self.listener = callback

    def generate_loop(self):
        while self.running and self.generated_count < 300:
            raw = self.generate_one_data()
            if self.listener:
                self.listener(raw)
            self.generated_count += 1
            time.sleep(1)

    def generate_one_data(self) -> RawData:
        id = str(uuid.uuid4())
        timestamp = self.current_timestamp
        source = f"source_{random.randint(1, 10)}"
        attributes = {}
        type_ = str(random.choice([1, 2, 3]))
        attributes['type'] = type_
        if type_ == '1':
            attributes['temperature'] = str(random.uniform(0, 200))
        elif type_ == '2':
            attributes['time_of_day'] = str(random.uniform(0, 24))
            attributes['used_device'] = str(random.choice([True, False]))
        elif type_ == '3':
            attributes['volume'] = str(random.uniform(0, 2000))
            attributes['ip'] = f"192.168.{random.randint(0,255)}.{random.randint(0,255)}"
        self.current_timestamp += datetime.timedelta(hours=1)
        return RawData(id, timestamp, source, attributes)

class GuiAlertService(IAlertService):
    def __init__(self, app, auto_confirm_timeout: Optional[int] = 120):
        self.alerts: Dict[str, Alert] = {}
        self.app = app  # Reference to app for GUI update
        # auto_confirm_timeout: seconds to wait before auto-confirm; None or 0 = disabled
        self.auto_confirm_timeout = auto_confirm_timeout
        # Доп. словарь для времени подтверждения alert'ов (alert_id -> datetime)
        self.confirmed_times: Dict[str, datetime.datetime] = {}

    def send_alert(self, anomaly: Anomaly, user: User):
        """
        Вызывается из потока генератора данных. НЕ делаем прямых GUI-вызовов.
        Просто создаём alert, запускаем авто-подтверждение (если включено)
        и запланируем обновление GUI в главном потоке (но не переключаем вкладку).
        """
        alert_id = str(uuid.uuid4())
        message = f"Alert for user {user.username}: Anomaly {anomaly.description} Score: {anomaly.score}"
        alert = Alert(alert_id, anomaly.anomaly_id, datetime.datetime.now(), message, "open")
        self.alerts[alert_id] = alert

        # Запускаем авто-подтверждение ТОЛЬКО если таймаут задан и больше 0
        if self.auto_confirm_timeout and self.auto_confirm_timeout > 0:
            threading.Thread(target=self.auto_confirm, args=(alert_id,), daemon=True).start()

        # Обновляем GUI безопасно — только перерисовка Alerts (если он открыт)
        # Не переключаемся автоматически на вкладку Alerts (убирает мигание).
        try:
            if getattr(self.app, 'current_view', None) == 'Alerts':
                # schedule update in main thread
                self.app.after(0, lambda: self._safe_refresh_alerts_view())
            else:
                # можно обновить счётчик/бейдж на сайдбаре здесь, если вы хотите:
                # self.app.after(0, lambda: self._update_sidebar_alert_count())
                pass
        except Exception:
            pass

    def _safe_refresh_alerts_view(self):
        """Вызывается в главном потоке, чтобы безопасно обновить AlertsView."""
        try:
            if 'Alerts' in self.app.views:
                # вызываем метод update_alerts у view (если он есть)
                view = self.app.views['Alerts']
                try:
                    view.update_alerts()
                except Exception:
                    # для совместимости, можно переключиться и заново отрендерить
                    try:
                        self.app.switch_view('Alerts')
                    except Exception:
                        pass
        except Exception:
            pass

    def auto_confirm(self, alert_id: str):
        """Фоновой таймер — выполняется в отдельном потоке, но все GUI-операции делаются через app.after."""
        try:
            time.sleep(self.auto_confirm_timeout)
            # только подтвердить, если alert всё ещё открыт
            if alert_id in self.alerts and self.alerts[alert_id].status == 'open':
                # обновление статуса сделаем в главном потоке (через after), чтобы не трогать tkinter из фонового потока
                def do_confirm():
                    # это будет выполнено в главном потоке
                    self.update_alert_status(alert_id, 'confirmed')
                try:
                    self.app.after(0, do_confirm)
                except Exception:
                    # если app уже закрывается или что-то пошло не так
                    try:
                        do_confirm()
                    except Exception:
                        pass
        except Exception:
            pass

    def update_alert_status(self, alert_id: str, new_status: str):
        """
        Обновляет статус и фиксирует время подтверждения.
        Может вызываться из главного потока (preferred) или через app.after.
        """
        if alert_id in self.alerts:
            self.alerts[alert_id].status = new_status
            if new_status == 'confirmed':
                self.confirmed_times[alert_id] = datetime.datetime.now()
            else:
                if alert_id in self.confirmed_times:
                    del self.confirmed_times[alert_id]

            # GUI-обновление: вызываем в главном потоке через after, только если Alerts открыт
            try:
                if getattr(self.app, 'current_view', None) == 'Alerts':
                    # schedule refresh — _safe_refresh_alerts_view сама выполнится в главном потоке
                    try:
                        self.app.after(0, lambda: self._safe_refresh_alerts_view())
                    except Exception:
                        pass
            except Exception:
                pass

    def get_alerts(self) -> List[Alert]:
        return list(self.alerts.values())
# Controllers
class ConfigController:
    def __init__(self, settings_repo: ISettingsRepository):
        self.settings_repo = settings_repo

    def get_settings_for_user(self, user_id: str) -> DetectionSettings:
        return self.settings_repo.load_settings(user_id)

    def save_user_settings(self, settings: DetectionSettings):
        self.settings_repo.save_settings(settings)

    def trigger_model_retraining(self):
        # Implement training trigger
        historical = self.app.data_storage.get_historical_data(datetime.datetime.min, datetime.datetime.max)
        self.app.detector.train_model(historical)

class AnomalyController:
    def __init__(self, storage: IDataStorage, detector: IAnomalyDetector, alert_service: IAlertService, config_controller: ConfigController, user: User):
        self.storage = storage
        self.detector = detector
        self.alert_service = alert_service
        self.config_controller = config_controller
        self.user = user

    def process_new_raw_data(self, raw_data: RawData):
        prepared = self.preprocess_data(raw_data)
        self.storage.store_raw_data(raw_data)
        self.storage.store_prepared_data(prepared)
        settings = self.config_controller.get_settings_for_user(self.user.user_id)
        anomaly = self.detector.detect(prepared, settings)
        if anomaly:
            self.storage.store_anomaly(anomaly)
            self.alert_service.send_alert(anomaly, self.user)

    def update_global_sensitivity(self, new_sensitivity: float):
        self.detector.set_global_sensitivity(new_sensitivity)

    def get_anomalies_in_period(self, start_time: datetime.datetime, end_time: datetime.datetime, role: str) -> List[Anomaly]:
        return self.storage.get_anomalies(role, start_time, end_time)

    def acknowledge_alert(self, alert_id: str):
        self.alert_service.update_alert_status(alert_id, "acknowledged")

    def preprocess_data(self, raw_data: RawData) -> PreparedData:
        data_type = raw_data.attributes.get('type', '')
        features = []
        type_str = ''
        if data_type == '1':
            temp = float(raw_data.attributes.get('temperature', '0'))
            features = [temp]
            type_str = 'sensor'
        elif data_type == '2':
            time_of_day = float(raw_data.attributes.get('time_of_day', '0'))
            features = [time_of_day]
            type_str = 'transaction'
        elif data_type == '3':
            volume = float(raw_data.attributes.get('volume', '0'))
            features = [volume]
            type_str = 'traffic'
        else:
            raise ValueError("Unknown data type")
        return PreparedData(raw_data.id, raw_data.timestamp, type_str, features)

# Views
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
        tk.Label(self.app.content, text="Dashboard - Current Anomalies", font=("Arial", 16), bg="#001f3f", fg="white").pack(pady=10)
        self.update_graphs()

    def stop_update(self):
        if self.update_id:
            self.app.after_cancel(self.update_id)
            self.update_id = None

    def update_graphs(self):
        if self.app.current_view != self.get_view_name():
            return
        # Защита: если виджеты были уничтожены при переключении view, сбросим состояние
        try:
            if getattr(self, 'anomaly_list', None) is not None:
                if not self.anomaly_list.winfo_exists():
                    self.canvas = None
                    self.canvas2 = None
                    self.anomaly_list = None
                    self.ax = None
                    self.ax2 = None
        except tk.TclError:
            self.canvas = None
            self.canvas2 = None
            self.anomaly_list = None
            self.ax = None
            self.ax2 = None

        if self.canvas:
            if self.ax:
                self.ax.clear()
            if self.canvas2 and self.ax2:
                self.ax2.clear()
            try:
                if getattr(self, 'anomaly_list', None) is not None and self.anomaly_list.winfo_exists():
                    self.anomaly_list.delete(0, tk.END)
                else:
                    self.canvas = None
                    self.canvas2 = None
                    self.anomaly_list = None
                    self.ax = None
                    self.ax2 = None
            except tk.TclError:
                # Если удаление вызвало ошибку — сбросим, чтобы пересоздать на следующем цикле
                self.canvas = None
                self.canvas2 = None
                self.anomaly_list = None
                self.ax = None
                self.ax2 = None
        else:
            # Создаём виджеты заново
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
            tk.Label(list_frame, text="Anomalies", font=("Arial", 12), bg='#001f3f', fg="white").pack()
            self.anomaly_list = tk.Listbox(list_frame, height=20, width=50, bg='#0a192f', fg="white",
                                           selectbackground="cyan")
            self.anomaly_list.pack()
            # Перенёс привязку обработчика выбора в handle_input() — см. handle_input ниже

        # Сбор данных и отрисовка (без start_time / end_time — это для HistoricalView)
        historical_data = self.app.data_storage.get_historical_data(datetime.datetime.min, datetime.datetime.max)
        filtered_data = [d for d in historical_data if self.app.filter_by_role(d.data_type)]

        # если данных для роли нет — планируем повтор
        if not filtered_data:
            self.update_id = self.app.after(1000, self.update_graphs)
            return

        # агрегируем по дням
        daily_features = defaultdict(list)
        for d in filtered_data:
            day = d.timestamp.date()
            daily_features[day].append(d.features[0])
        daily_times = sorted(daily_features.keys())
        daily_avg = [sum(daily_features[day]) / len(daily_features[day]) for day in daily_times]

        # получаем аномалии через storage (Dashboard показывает текущую роль)
        anomalies = self.app.data_storage.get_anomalies(self.app.role)
        daily_anomaly_scores = defaultdict(list)
        for a in anomalies:
            day = a.detection_time.date()
            daily_anomaly_scores[day].append(a.score)
        daily_anomaly_avg = [(sum(daily_anomaly_scores.get(day, [0])) / len(
            daily_anomaly_scores.get(day, [1]))) if daily_anomaly_scores.get(day) else None for day in daily_times]

        # рисуем основной график (если ось существует)
        if self.ax:
            self.ax.plot(daily_times, daily_avg, label='Avg Feature', color='cyan')
            self.ax.scatter([day for i, day in enumerate(daily_times) if daily_anomaly_avg[i] is not None],
                            [val for val in daily_anomaly_avg if val is not None],
                            color='red', label='Avg Anomaly Score')
            self.ax.set_xlabel("Day")
            self.ax.set_ylabel("Value")
            self.ax.set_facecolor('#001f3f')
            self.ax.tick_params(colors='white')
            for spine in ['bottom', 'top', 'left', 'right']:
                self.ax.spines[spine].set_color('white')
            if self.app.role == 'equipment':
                self.ax.set_title('Daily Avg Temperature', color='white')
            elif self.app.role == 'fraud':
                self.ax.set_title('Daily Avg Transaction Time', color='white')
            elif self.app.role == 'security':
                self.ax.set_title('Daily Avg Traffic Volume', color='white')
            self.ax.legend()
            plt.setp(self.ax.get_xticklabels(), rotation=45, ha="right", color='white')
            self.canvas.draw()

        # дополнительный график для security (IP частоты)
        if self.app.role == 'security' and getattr(self, 'ax2', None):
            ips = [raw.attributes.get('ip') for raw in self.app.data_storage.raw_data if
                   raw.attributes.get('type') == '3' and 'ip' in raw.attributes]
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

        # обновляем список аномалий (если список существует)
        try:
            if getattr(self, 'anomaly_list', None) is not None and self.anomaly_list.winfo_exists():
                for a in anomalies:
                    self.anomaly_list.insert(tk.END, f"{a.description} - Score: {a.score}")
        except tk.TclError:
            # при проблеме — сбросим, чтобы на следующем цикле пересоздать виджеты
            self.canvas = None
            self.canvas2 = None
            self.anomaly_list = None
            self.ax = None
            self.ax2 = None

        self.update_id = self.app.after(1000, self.update_graphs)

    def handle_input(self):
        """
        Перенёс сюда обработку взаимодействия пользователя с виджетом списка аномалий.
        Вызывается из App после render() через views[...].handle_input().
        """
        try:
            # Если список аномалий существует и жив — привязываем обработчик выбора
            if getattr(self, 'anomaly_list', None) is not None and self.anomaly_list.winfo_exists():
                # Убираем предыдущие бинды (если были), затем ставим новый
                try:
                    self.anomaly_list.unbind('<<ListboxSelect>>')
                except Exception:
                    pass
                # биндим только если есть обработчик show_anomaly_details
                if hasattr(self, 'show_anomaly_details'):
                    self.anomaly_list.bind('<<ListboxSelect>>', self.show_anomaly_details)
                    # Дополнительно: двойной клик откроет детали (удобно в GUI)
                    try:
                        self.anomaly_list.unbind('<Double-1>')
                    except Exception:
                        pass
                    self.anomaly_list.bind('<Double-1>', lambda e: self.show_anomaly_details(e))
        except tk.TclError:
            # Виджет мог быть уничтожен между render и handle_input — игнорируем
            pass

    def show_anomaly_details(self, event):
        selection = self.anomaly_list.curselection()
        if selection:
            index = selection[0]
            anomalies = self.app.data_storage.get_anomalies(self.app.role)
            # ограничимся индексом, если аномалий меньше — защитная проверка
            if index < len(anomalies):
                a = anomalies[index]
                # Открываем унифицированный диалог подтверждения
                AnomalyConfirmationDialog(self.app, a)

    def confirm_anomaly(self, alert_id: str, window):
        self.app.alert_service.update_alert_status(alert_id, 'confirmed')
        window.destroy()

    def false_positive(self, alert_id: str, window):
        self.app.alert_service.update_alert_status(alert_id, 'false_positive')
        self.app.trigger_retraining()  # Optional retrain on false positive
        window.destroy()

    def get_view_name(self) -> str:
        return "Dashboard"

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
        tk.Label(self.app.content, text="Historical Analysis", font=("Arial", 16), bg="#001f3f", fg="white").pack(pady=10)
        # Date filters
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
        # Защита: если canvas был уничтожен извне, сбрасываем состояние
        try:
            if getattr(self, 'canvas', None) is not None:
                if not self.canvas.get_tk_widget().winfo_exists():
                    self.canvas = None
                    self.ax = None
        except tk.TclError:
            self.canvas = None
            self.ax = None

        # Получаем ВСЕ аномалии за период (storage)
        all_anomalies = self.app.anomaly_controller.get_anomalies_in_period(self.start_time, self.end_time,
                                                                            self.app.role)

        # Фильтруем через alert_service — только confirmed alerts
        confirmed_ids = set()
        for al in self.app.alert_service.get_alerts():
            if al.status == 'confirmed':
                confirmed_ids.add(al.anomaly_id)

        anomalies = [a for a in all_anomalies if a.anomaly_id in confirmed_ids]

        # Создаём canvas/axis если нужно
        if not getattr(self, 'canvas', None):
            self.fig = Figure(figsize=(10, 5), dpi=100, facecolor='#001f3f')
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.app.content)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Очищаем и рисуем график количества подтверждённых аномалий по дням
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
            self.ax.text(0.5, 0.5, "No confirmed anomalies in the selected range", ha='center', va='center',
                         transform=self.ax.transAxes, color='white')
            self.ax.set_title('Daily Confirmed Anomaly Counts', color='white')

        self.ax.set_xlabel("Day")
        self.ax.set_ylabel("Count")
        self.ax.set_facecolor('#001f3f')
        self.ax.tick_params(colors='white')
        for spine in ['bottom', 'top', 'left', 'right']:
            self.ax.spines[spine].set_color('white')
        plt.setp(self.ax.get_xticklabels(), rotation=45, ha="right", color='white')
        self.canvas.draw()

        # Список подтверждённых аномалий внизу (results_frame)
        if getattr(self, 'results_frame', None) is None or not getattr(self, 'results_frame').winfo_exists():
            self.results_frame = tk.Frame(self.app.content, bg='#001f3f')
            self.results_frame.pack(fill=tk.X, pady=10)
        else:
            for w in self.results_frame.winfo_children():
                w.destroy()

        if anomalies:
            for a in anomalies:
                # Кликабельный label — по клику открываем тот же диалог подтверждения (в случае необходимости просмотра истории)
                lbl = ttk.Label(self.results_frame, text=f"{a.description} at {a.detection_time}")
                lbl.pack(anchor='w', pady=2, padx=5)
                lbl.bind("<Button-1>", lambda e, anomaly=a: AnomalyConfirmationDialog(self.app, anomaly))
        else:
            ttk.Label(self.results_frame, text="No confirmed anomalies found for selected period.").pack(anchor='w')

        self.update_id = self.app.after(1000, self.update_graphs)

    def apply_filter(self):
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

class AnomalyConfirmationDialog:
    def __init__(self, app, anomaly: Anomaly):
        self.app = app
        self.anomaly = anomaly

        # Найдём (если есть) связанный alert
        alerts = self.app.alert_service.get_alerts()
        self.alert = next((al for al in alerts if al.anomaly_id == anomaly.anomaly_id), None)

        # Если alert отсутствует, создадим его (send_alert) — тогда он будет в списке alert_service
        if self.alert is None:
            # send_alert создаёт новый Alert со статусом 'open'
            self.app.alert_service.send_alert(anomaly, self.app.current_user)
            # после отправки — обновим локальную ссылку (alert_service хранит их)
            alerts = self.app.alert_service.get_alerts()
            self.alert = next((al for al in alerts if al.anomaly_id == anomaly.anomaly_id), None)

        # Создаём окно диалога
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
        tk.Label(self.win, text=f"Description: {a.description}", bg='#001f3f', fg="white", wraplength=500, justify='left').pack(anchor='w', padx=10, pady=2)
        tk.Label(self.win, text=f"Severity: {a.severity}", bg='#001f3f', fg="white").pack(anchor='w', padx=10, pady=6)

        # Статус alert (если есть)
        status_text = self.alert.status if self.alert is not None else "no alert"
        self.status_label = tk.Label(self.win, text=f"Alert status: {status_text}", bg='#001f3f', fg="white")
        self.status_label.pack(padx=10, pady=4)

        # Кнопки: Confirm / False Positive / Close
        btn_frame = tk.Frame(self.win, bg='#001f3f')
        btn_frame.pack(pady=8, padx=10, fill='x')

        confirm_btn = ttk.Button(btn_frame, text="Confirm", command=self.confirm)
        confirm_btn.pack(side=tk.LEFT, expand=True, fill='x', padx=5)

        false_btn = ttk.Button(btn_frame, text="False Positive", command=self.false_positive)
        false_btn.pack(side=tk.LEFT, expand=True, fill='x', padx=5)

        close_btn = ttk.Button(btn_frame, text="Close", command=self.win.destroy)
        close_btn.pack(side=tk.LEFT, expand=True, fill='x', padx=5)

        # Если alert уже подтверждён — отключим Confirm
        if self.alert and self.alert.status == 'confirmed':
            confirm_btn.state(['disabled'])
            self.status_label.config(text=f"Alert status: {self.alert.status}")

    def confirm(self):
        # Если alert не найден — создадим его перед подтверждением
        if self.alert is None:
            self.app.alert_service.send_alert(self.anomaly, self.app.current_user)
            alerts = self.app.alert_service.get_alerts()
            self.alert = next((al for al in alerts if al.anomaly_id == self.anomaly.anomaly_id), None)

        if self.alert:
            self.app.alert_service.update_alert_status(self.alert.alert_id, 'confirmed')
            # Обновить label
            self.status_label.config(text=f"Alert status: confirmed")
            messagebox.showinfo("Confirmed", "Anomaly confirmed.")
            # Обновим представления, чтобы изменения сразу отобразились
            if self.app.current_view == 'Alerts' or self.app.current_view == 'Historical Analysis' or self.app.current_view == 'Dashboard':
                self.app.switch_view(self.app.current_view)
            self.win.destroy()

    def false_positive(self):
        # Если alert не найден — создадим его, потом пометим false_positive (чтобы логика осталась общей)
        if self.alert is None:
            self.app.alert_service.send_alert(self.anomaly, self.app.current_user)
            alerts = self.app.alert_service.get_alerts()
            self.alert = next((al for al in alerts if al.anomaly_id == self.anomaly.anomaly_id), None)

        if self.alert:
            self.app.alert_service.update_alert_status(self.alert.alert_id, 'false_positive')
            # optional retrain
            try:
                self.app.trigger_retraining()
            except Exception:
                pass
            messagebox.showinfo("Marked", "Anomaly marked as false positive.")
            if self.app.current_view == 'Alerts' or self.app.current_view == 'Historical Analysis' or self.app.current_view == 'Dashboard':
                self.app.switch_view(self.app.current_view)
            self.win.destroy()


class AlertsView(IView):
    def __init__(self, app):
        self.app = app
        self.update_id = None

    def render(self):
        tk.Label(self.app.content, text="Alerts", font=("Arial", 16), bg="#001f3f", fg="white").pack(pady=10)
        self.update_alerts()

    def stop_update(self):
        if self.update_id:
            self.app.after_cancel(self.update_id)
            self.update_id = None

    def update_alerts(self):
        if self.app.current_view != self.get_view_name():
            return
        # Очищаем содержимое (кроме заголовка) — как раньше
        for widget in self.app.content.winfo_children()[1:]:
            widget.destroy()

        role_map = {
            'security': 'traffic',
            'equipment': 'sensor',
            'fraud': 'transaction'
        }
        allowed_type = role_map.get(self.app.role, '')

        # Собираем ВСЕ confirmed alerts, относящиеся к роли
        confirmed_alerts = []
        for al in self.app.alert_service.get_alerts():
            if al.status == 'confirmed':
                anomaly = self.app.data_storage.get_anomaly(al.anomaly_id)
                if anomaly and anomaly.description.startswith(allowed_type + ":"):
                    confirmed_alerts.append((al, anomaly))

        # Разделяем на новые (подтверждены после последнего захода на вкладку) и старые
        new_alerts = []
        old_alerts = []
        last_visit = getattr(self.app, 'last_alerts_view_time', datetime.datetime.min)
        for al, anomaly in confirmed_alerts:
            # смотрим время подтверждения из alert_service.confirmed_times (если есть)
            conf_time = self.app.alert_service.confirmed_times.get(al.alert_id, None)
            # Если время подтверждения неизвестно, используем время поднятия alert (time_raised) как fallback
            if conf_time is None:
                conf_time = al.time_raised
            if conf_time > last_visit:
                new_alerts.append((al, anomaly))
            else:
                old_alerts.append((al, anomaly))

        # Секция: New confirmed alerts
        if new_alerts:
            header = ttk.Label(self.app.content, text=f"New Confirmed Alerts ({len(new_alerts)})",
                               font=("Arial", 12, "bold"), background='#001f3f', foreground='yellow')
            header.pack(fill=tk.X, pady=(5, 2))
            for al, anomaly in new_alerts:
                frame = ttk.Frame(self.app.content)
                frame.pack(fill=tk.X, pady=2, padx=5)
                # Пометка NEW
                new_badge = tk.Label(frame, text="NEW", bg='red', fg='white', padx=6)
                new_badge.pack(side=tk.LEFT, padx=(0, 6))
                ttk.Label(frame, text=al.message).pack(side=tk.LEFT, expand=True, fill=tk.X)
                # Кнопка Acknowledge (если нужно)
                ttk.Button(frame, text="Acknowledge",
                           command=lambda aid=al.alert_id: self.app.anomaly_controller.acknowledge_alert(aid)).pack(
                    side=tk.RIGHT)

        # Секция: Older confirmed alerts
        if old_alerts:
            header2 = ttk.Label(self.app.content, text="Confirmed Alerts", font=("Arial", 12, "bold"),
                                background='#001f3f', foreground='white')
            header2.pack(fill=tk.X, pady=(10, 2))
            for al, anomaly in old_alerts:
                frame = ttk.Frame(self.app.content)
                frame.pack(fill=tk.X, pady=2, padx=5)
                ttk.Label(frame, text=al.message).pack(side=tk.LEFT, expand=True, fill=tk.X)
                ttk.Button(frame, text="Acknowledge",
                           command=lambda aid=al.alert_id: self.app.anomaly_controller.acknowledge_alert(aid)).pack(
                    side=tk.RIGHT)

        # Если нет ни новых, ни старых — покажем сообщение
        if not new_alerts and not old_alerts:
            ttk.Label(self.app.content, text="No confirmed alerts for your role.", background='#001f3f').pack(pady=10)

        # Обновляем время последнего захода — ставим после того как мы вычислили new_alerts
        self.app.last_alerts_view_time = datetime.datetime.now()

        # Планируем следующий апдейт
        self.update_id = self.app.after(1000, self.update_alerts)

    def handle_input(self):
        pass

    def get_view_name(self) -> str:
        return "Alerts"

class SettingsView(IView):
    def __init__(self, app):
        self.app = app

    def render(self):
        tk.Label(self.app.content, text="Settings", font=("Arial", 16), bg="#001f3f", fg="white").pack(pady=10)
        settings = self.app.config_controller.get_settings_for_user(self.app.current_user.user_id)

        tk.Label(self.app.content, text="Sensitivity:", font=("Arial", 12), bg="#001f3f", fg="white").pack()

        # Центрирующий контейнер, чтобы слайдер был по центру и имел большую ширину
        center_container = tk.Frame(self.app.content, bg="#001f3f")
        center_container.pack(fill=tk.X, pady=10)

        # Сам фрейм с ползунком; padx регулирует отступы слева/справа -> визуально центрирует
        sens_frame = tk.Frame(center_container, bg="#001f3f")
        sens_frame.pack(padx=150, fill=tk.X)

        self.sens_label = tk.Label(sens_frame, text=f"{settings.sensitivity:.2f}", bg="#001f3f", fg="white")
        self.sens_label.pack(side=tk.LEFT, padx=10)

        # Увеличенный ползунок (length) и растяжение по X
        self.sens_scale = ttk.Scale(sens_frame, from_=0.0, to=1.0, orient='horizontal',
                                    value=settings.sensitivity, command=self.update_label, length=600)
        self.sens_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        ttk.Button(self.app.content, text="Set Sensitivity", command=self.set_sensitivity).pack(pady=5)
        ttk.Button(self.app.content, text="Tune Sensitivity", command=self.tune_sensitivity).pack(pady=5)

    def update_label(self, value):
        self.sens_label.config(text=f"{float(value):.2f}")

    def set_sensitivity(self):
        s = self.sens_scale.get()
        settings = self.app.config_controller.get_settings_for_user(self.app.current_user.user_id)
        settings.sensitivity = s
        self.app.config_controller.save_user_settings(settings)
        self.app.anomaly_controller.update_global_sensitivity(s)
        messagebox.showinfo("Success", f"Sensitivity set to {s:.2f}")
        self.app.switch_view("Settings")

    def tune_sensitivity(self):
        self.app.trigger_retraining()
        messagebox.showinfo("Success", f"Tuned sensitivity to {self.app.detector.global_sensitivity:.2f}")
        self.app.switch_view("Settings")

    def handle_input(self):
        pass

    def get_view_name(self) -> str:
        return "Settings"

# App
class AnomalyDetectionApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Anomaly Detector")
        self.geometry("1200x800")
        self.configure(bg="#001f3f")  # Navy blue
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('.', background='#001f3f', foreground='white')
        self.style.configure('TButton', background='darkgreen', foreground='white')
        self.style.configure('TLabel', background='#001f3f', foreground='white')
        self.style.configure('TEntry', fieldbackground='#0a192f', foreground='white')
        self.style.configure('Horizontal.TScale', background='#001f3f')
        self.data_source = None
        self.data_storage = None
        self.detector = None
        self.alert_service = None
        self.settings_repo = None
        self.anomaly_controller = None
        self.config_controller = None
        self.current_user = None
        self.current_view = None
        self.role = None
        self.views = {}
        self.last_alerts_view_time = datetime.datetime.now()
        # Hardcoded users
        self.users = {
            'analyst': {'password': 'pass1', 'role': 'security'},
            'specialist': {'password': 'pass2', 'role': 'equipment'},
            'manager': {'password': 'pass3', 'role': 'fraud'}
        }
        self.show_login()

    def show_login(self):
        self.login_frame = ttk.Frame(self)
        self.login_frame.pack(fill=tk.BOTH, expand=True, pady=100)
        ttk.Label(self.login_frame, text="Username:").pack(pady=5)
        self.username_entry = ttk.Entry(self.login_frame)
        self.username_entry.pack(pady=5)
        ttk.Label(self.login_frame, text="Password:").pack(pady=5)
        self.password_entry = ttk.Entry(self.login_frame, show="*")
        self.password_entry.pack(pady=5)
        ttk.Button(self.login_frame, text="Login", command=self.login).pack(pady=10)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if username in self.users and self.users[username]['password'] == password:
            self.role = self.users[username]['role']
            self.current_user = User(username, username, self.role, f"{username}@example.com")
            self.login_frame.destroy()
            self.setup_dependencies()
            self.initialize()
            self.setup_gui()
        else:
            messagebox.showerror("Error", "Invalid credentials")

    def setup_dependencies(self):
        self.data_source = SimulatedDataSource()
        self.data_storage = InMemoryDataStorage()
        self.detector = SimpleAnomalyDetector()
        self.alert_service = GuiAlertService(self, auto_confirm_timeout=120)
        self.settings_repo = JsonSettingsRepository()
        self.config_controller = ConfigController(self.settings_repo)
        self.anomaly_controller = AnomalyController(self.data_storage, self.detector, self.alert_service, self.config_controller, self.current_user)

    def initialize(self):
        self.data_source.connect()
        self.data_source.register_data_listener(self.anomaly_controller.process_new_raw_data)

    def setup_gui(self):
        # Sidebar
        self.sidebar = tk.Frame(self, bg="#000080", width=200)  # Darker navy
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(self.sidebar, text="Anomaly Detector", bg="#000080", fg="yellow", font=("Arial", 14, "bold")).pack(pady=20)
        tk.Label(self.sidebar, text=f"User: {self.current_user.username}", bg="#000080", fg="white", font=("Arial", 12)).pack(pady=10)
        self.menu_buttons = {}
        menus = ["Dashboard", "Historical Analysis", "Alerts", "Settings"]
        for menu in menus:
            btn = ttk.Button(self.sidebar, text=menu, command=lambda m=menu: self.switch_view(m))
            btn.pack(fill=tk.X, pady=10)
            self.menu_buttons[menu] = btn
        ttk.Button(self.sidebar, text="Logout", command=self.quit).pack(fill=tk.X, pady=10)
        # Content area
        self.content = tk.Frame(self, bg="#001f3f")
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # Create views
        self.views = {
            "Dashboard": MainMonitorView(self),
            "Historical Analysis": HistoricalView(self),
            "Alerts": AlertsView(self),
            "Settings": SettingsView(self)
        }
        self.switch_view("Dashboard")

    def switch_view(self, view):
        if self.current_view:
            self.views[self.current_view].stop_update()
        self.current_view = view
        for widget in self.content.winfo_children():
            widget.destroy()
        if view in self.views:
            self.views[view].render()
            self.views[view].handle_input()

    def filter_by_role(self, data_type: str) -> bool:
        role_map = {
            'security': 'traffic',
            'equipment': 'sensor',
            'fraud': 'transaction'
        }
        return data_type == role_map.get(self.role, '')

    def trigger_retraining(self):
        historical = self.data_storage.get_historical_data(datetime.datetime.min, datetime.datetime.max)
        filtered = [d for d in historical if self.filter_by_role(d.data_type)]
        self.detector.train_model(filtered)

    def run(self):
        self.mainloop()

if __name__ == "__main__":
    app = AnomalyDetectionApp()
    app.run()