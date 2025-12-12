import json
import os
from interfaces import ISettingsRepository
from models import DetectionSettings

class JsonSettingsRepository(ISettingsRepository):
    def __init__(self, file_path="settings.json"):
        self.file_path = file_path
        self.settings_dict = {}
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                self.settings_dict = json.load(f)

    def load_settings(self, user_id: str) -> DetectionSettings:
        data = self.settings_dict.get(user_id, 
                                     {"sensitivity": 0.5, "monitored_sources": ["any"]})
        return DetectionSettings(user_id, data["sensitivity"], data["monitored_sources"])

    def save_settings(self, settings: DetectionSettings):
        self.settings_dict[settings.user_id] = {
            "sensitivity": settings.sensitivity,
            "monitored_sources": settings.monitored_sources
        }
        with open(self.file_path, 'w') as f:
            json.dump(self.settings_dict, f)