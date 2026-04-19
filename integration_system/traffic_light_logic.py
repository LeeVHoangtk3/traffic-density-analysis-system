# integration/traffic_light_logic.py


class TrafficLightOptimizer:
    def optimize(self, congestion_level):
        normalized = str(congestion_level).strip().lower()

        if normalized == "low":
            green_time = 20
        elif normalized == "medium":
            green_time = 40
        elif normalized == "high":
            green_time = 60
        else:
            green_time = 90

        return {"green_time": green_time}
