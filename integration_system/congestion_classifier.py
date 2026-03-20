class CongestionClassifier:
    def classify(self, vehicle_count):
        if vehicle_count < 15:
            return "Low"
        elif vehicle_count < 30:
            return "Medium"
        elif vehicle_count < 50:
            return "High"
        else:
            return "Severe"