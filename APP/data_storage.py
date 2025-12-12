import datetime
from typing import List, Optional
from collections import defaultdict
from interfaces import IDataStorage
from models import RawData, PreparedData, Anomaly

class InMemoryDataStorage(IDataStorage):
    def __init__(self):
        self.raw_data: List[RawData] = []
        self.prepared_data: List[PreparedData] = []
        self.anomalies: List[Anomaly] = []

    def store_raw_data(self, data: RawData):
        self.raw_data.append(data)

    def store_prepared_data(self, data: PreparedData):
        self.prepared_data.append(data)

    def get_historical_data(self, start_time: datetime.datetime, 
                           end_time: datetime.datetime) -> List[PreparedData]:
        return [d for d in self.prepared_data if start_time <= d.timestamp <= end_time]

    def store_anomaly(self, anomaly: Anomaly):
        self.anomalies.append(anomaly)

    def get_anomalies(self, role: str, 
                     start_time: datetime.datetime = datetime.datetime.min,
                     end_time: datetime.datetime = datetime.datetime.max) -> List[Anomaly]:
        role_map = {
            'security': 'traffic',
            'equipment': 'sensor',
            'fraud': 'transaction'
        }
        allowed_type = role_map.get(role, '')
        return [a for a in self.anomalies 
                if a.description.startswith(allowed_type + ":") 
                and start_time <= a.detection_time <= end_time]

    def get_anomaly(self, anomaly_id: str) -> Optional[Anomaly]:
        return next((a for a in self.anomalies if a.anomaly_id == anomaly_id), None)