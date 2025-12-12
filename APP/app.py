import tkinter as tk
from tkinter import messagebox, ttk
import datetime
from models import User
from data_sources import SimulatedDataSource
from data_storage import InMemoryDataStorage
from detectors import SimpleAnomalyDetector
from alert_service import GuiAlertService
from repositories import JsonSettingsRepository
from controllers import ConfigController, AnomalyController
from views import MainMonitorView, HistoricalView, AlertsView, SettingsView

class AnomalyDetectionApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Anomaly Detector")
        self.geometry("1200x800")
        self.configure(bg="#001f3f")
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self._configure_styles()
        
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

    def _configure_styles(self):
        """Configure ttk styles"""
        self.style.configure('.', background='#001f3f', foreground='white')
        self.style.configure('TButton', background='darkgreen', foreground='white')
        self.style.configure('TLabel', background='#001f3f', foreground='white')
        self.style.configure('TEntry', fieldbackground='#0a192f', foreground='white')
        self.style.configure('Horizontal.TScale', background='#001f3f')

    def show_login(self):
        """Display login screen"""
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
        """Handle login authentication"""
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
        """Initialize all dependencies"""
        self.data_source = SimulatedDataSource()
        self.data_storage = InMemoryDataStorage()
        self.detector = SimpleAnomalyDetector()
        self.alert_service = GuiAlertService(self, auto_confirm_timeout=120)
        self.settings_repo = JsonSettingsRepository()
        self.config_controller = ConfigController(self.settings_repo)
        self.anomaly_controller = AnomalyController(
            self.data_storage, self.detector, self.alert_service, 
            self.config_controller, self.current_user
        )

    def initialize(self):
        """Initialize data source and listeners"""
        self.data_source.connect()
        self.data_source.register_data_listener(self.anomaly_controller.process_new_raw_data)

    def setup_gui(self):
        """Setup the main GUI layout"""
        # Sidebar
        self.sidebar = tk.Frame(self, bg="#000080", width=200)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(self.sidebar, text="Anomaly Detector", bg="#000080", 
                 fg="yellow", font=("Arial", 14, "bold")).pack(pady=20)
        tk.Label(self.sidebar, text=f"User: {self.current_user.username}", 
                 bg="#000080", fg="white", font=("Arial", 12)).pack(pady=10)
        
        # Menu buttons
        self.menu_buttons = {}
        menus = ["Dashboard", "Historical Analysis", "Alerts", "Settings"]
        for menu in menus:
            btn = ttk.Button(self.sidebar, text=menu, 
                           command=lambda m=menu: self.switch_view(m))
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
        """Switch between different views"""
        if self.current_view:
            self.views[self.current_view].stop_update()
        
        self.current_view = view
        
        # Clear current content
        for widget in self.content.winfo_children():
            widget.destroy()
        
        # Render new view
        if view in self.views:
            self.views[view].render()
            self.views[view].handle_input()

    def filter_by_role(self, data_type: str) -> bool:
        """Filter data based on user role"""
        role_map = {
            'security': 'traffic',
            'equipment': 'sensor',
            'fraud': 'transaction'
        }
        return data_type == role_map.get(self.role, '')

    def trigger_retraining(self):
        """Trigger model retraining"""
        historical = self.data_storage.get_historical_data(
            datetime.datetime.min, datetime.datetime.max
        )
        filtered = [d for d in historical if self.filter_by_role(d.data_type)]
        self.detector.train_model(filtered)

    def run(self):
        """Start the application"""
        self.mainloop()