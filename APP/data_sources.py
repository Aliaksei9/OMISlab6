import datetime
import uuid
import random
import threading
import time
from typing import Optional, Callable
from interfaces import IDataSource
from models import RawData

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
        data_id = str(uuid.uuid4())
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
        return RawData(data_id, timestamp, source, attributes)