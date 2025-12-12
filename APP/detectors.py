import uuid
from typing import List, Optional
from interfaces import IAnomalyDetector
from models import PreparedData, DetectionSettings, Anomaly

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