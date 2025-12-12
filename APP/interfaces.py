import abc
from typing import List, Optional, Callable
import datetime
from models import RawData, PreparedData, DetectionSettings, Anomaly, User

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
    def get_historical_data(self, start_time: datetime.datetime, 
                           end_time: datetime.datetime) -> List[PreparedData]:
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