class DensityEstimator:
    def __init__(self):
        self.current_count = 0

    def update(self, tracks):
        self.current_count = len(tracks)

    def get_density(self):
        if self.current_count < 5:
            return "LOW"
        elif self.current_count < 15:
            return "MEDIUM"
        return "HIGH"