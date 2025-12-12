import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional

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