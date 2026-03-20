# integration/traffic_light_logic.py

class TrafficLightOptimizer:

    def optimize(self, congestion_level):

        if congestion_level == "LOW":
            green_time = 20

        elif congestion_level == "MEDIUM":
            green_time = 40

        elif congestion_level == "HIGH":
            green_time = 60

        else:
            green_time = 90

        return {
            "green_time": green_time
        }