# integration/performance_monitor.py

import psutil
import time

class PerformanceMonitor:

    def monitor(self):

        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent

        return {
            "cpu_usage": cpu,
            "memory_usage": memory
        }