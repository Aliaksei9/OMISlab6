import datetime
from typing import List
from interfaces import ISettingsRepository, IDataStorage, IAnomalyDetector, IAlertService
from models import RawData, PreparedData, DetectionSettings, Anomaly, User

class ConfigController:
    def __init__(self, settings_repo: ISettingsRepository):
        self.settings_repo = settings_repo

    def get_settings_for_user(self, user_id: str) -> DetectionSettings:
        return self.settings_repo.load_settings(user_id)

    def save_user_settings(self, settings: DetectionSettings):
        self.settings_repo.save_settings(settings)

class AnomalyController:
    def __init__(self, storage: IDataStorage, detector: IAnomalyDetector, 
                 alert_service: IAlertService, config_controller: ConfigController, 
                 user: User):
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

    def get_anomalies_in_period(self, start_time: datetime.datetime, 
                               end_time: datetime.datetime, role: str) -> List[Anomaly]:
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