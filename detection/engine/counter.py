import time
from collections import defaultdict


class VehicleCounter:
    def __init__(self):
        self.total_counts = defaultdict(int)
        self.minute_counts = defaultdict(int)
        self.start_time = time.time()

    def count(self, class_name):
        self.total_counts[class_name] += 1
        self.minute_counts[class_name] += 1

    def get_totals(self):
        return dict(self.total_counts)

    def get_per_minute(self):
        if time.time() - self.start_time >= 60:
            data = dict(self.minute_counts)
            self.minute_counts.clear()
            self.start_time = time.time()
            return data
        return None