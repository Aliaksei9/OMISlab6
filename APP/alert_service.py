import uuid
import datetime
import threading
import time
from typing import Dict, List, Optional
from interfaces import IAlertService
from models import Anomaly, User, Alert

class GuiAlertService(IAlertService):
    def __init__(self, app, auto_confirm_timeout: Optional[int] = 120):
        self.alerts: Dict[str, Alert] = {}
        self.app = app
        self.auto_confirm_timeout = auto_confirm_timeout
        self.confirmed_times: Dict[str, datetime.datetime] = {}

    def send_alert(self, anomaly: Anomaly, user: User):
        alert_id = str(uuid.uuid4())
        message = f"Alert for user {user.username}: Anomaly {anomaly.description} Score: {anomaly.score}"
        alert = Alert(alert_id, anomaly.anomaly_id, datetime.datetime.now(), message, "open")
        self.alerts[alert_id] = alert

        if self.auto_confirm_timeout and self.auto_confirm_timeout > 0:
            threading.Thread(target=self.auto_confirm, args=(alert_id,), daemon=True).start()

        try:
            if getattr(self.app, 'current_view', None) == 'Alerts':
                self.app.after(0, lambda: self._safe_refresh_alerts_view())
        except Exception:
            pass

    def _safe_refresh_alerts_view(self):
        try:
            if 'Alerts' in self.app.views:
                view = self.app.views['Alerts']
                try:
                    view.update_alerts()
                except Exception:
                    try:
                        self.app.switch_view('Alerts')
                    except Exception:
                        pass
        except Exception:
            pass

    def auto_confirm(self, alert_id: str):
        try:
            time.sleep(self.auto_confirm_timeout)
            if alert_id in self.alerts and self.alerts[alert_id].status == 'open':
                def do_confirm():
                    self.update_alert_status(alert_id, 'confirmed')
                try:
                    self.app.after(0, do_confirm)
                except Exception:
                    try:
                        do_confirm()
                    except Exception:
                        pass
        except Exception:
            pass

    def update_alert_status(self, alert_id: str, new_status: str):
        if alert_id in self.alerts:
            self.alerts[alert_id].status = new_status
            if new_status == 'confirmed':
                self.confirmed_times[alert_id] = datetime.datetime.now()
            elif alert_id in self.confirmed_times:
                del self.confirmed_times[alert_id]

            try:
                if getattr(self.app, 'current_view', None) == 'Alerts':
                    try:
                        self.app.after(0, lambda: self._safe_refresh_alerts_view())
                    except Exception:
                        pass
            except Exception:
                pass

    def get_alerts(self) -> List[Alert]:
        return list(self.alerts.values())