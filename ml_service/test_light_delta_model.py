import unittest

from integration_system import system_runner
from ml_service.light_delta_model import LightDeltaModel


class FixedPredictor:
    def __init__(self, value):
        self.value = value

    def predict(self, _history):
        return self.value


class FakeDeltaModel:
    fallback_reason = None

    def __init__(self):
        self.features = []

    def predict_delta(self, feature_dict):
        self.features.append(feature_dict.copy())
        controlled_phase = feature_dict["controlled_phase"]
        baseline = feature_dict["baseline_green"]
        if controlled_phase == "phase_2":
            return 34 - baseline
        return 46 - baseline

    def prediction_source(self):
        return "xgboost"


class LightDeltaModelTest(unittest.TestCase):
    def build_model(self):
        model = LightDeltaModel()
        model._loaded = True
        model.predictors = {
            "straight": FixedPredictor(73),
            "left": FixedPredictor(39),
            "right": FixedPredictor(19),
        }
        return model

    def test_phase_1_delta_uses_phase_1_baseline(self):
        model = self.build_model()
        delta = model.predict_delta({
            "camera_id": "CAM_01",
            "controlled_phase": "phase_1",
            "baseline_green": 50,
            "queue_proxy": 12,
            "inbound_count": 80,
            "congestion_level": "high",
            "hour": 8,
            "day_of_week": 1,
        })

        self.assertEqual(delta, -4)

    def test_phase_2_delta_uses_phase_2_baseline(self):
        model = self.build_model()
        delta = model.predict_delta({
            "camera_id": "CAM_03",
            "controlled_phase": "phase_2",
            "baseline_green": 30,
            "queue_proxy": 12,
            "inbound_count": 80,
            "congestion_level": "high",
            "hour": 8,
            "day_of_week": 1,
        })

        self.assertEqual(delta, 4)

    def test_runner_passes_controlled_phase_and_baseline(self):
        previous_model = system_runner._light_model
        fake_model = FakeDeltaModel()
        system_runner._light_model = fake_model
        try:
            result = system_runner.TrafficLightOptimizer().optimize_with_ml(
                camera_id="CAM_01",
                queue_proxy=12,
                inbound_count=80,
                congestion_level="high",
                hour=8,
                dow=1,
            )
        finally:
            system_runner._light_model = previous_model

        self.assertEqual(result["mode"], "ml")
        self.assertEqual(result["controlled_phase"], "phase_1")
        self.assertEqual(result["baseline"], 50)
        self.assertEqual(result["green_time"], 46)
        self.assertEqual(result["delta"], -4)
        self.assertEqual(result["prediction_source"], "xgboost")
        self.assertEqual(fake_model.features[0]["controlled_phase"], "phase_1")
        self.assertEqual(fake_model.features[0]["baseline_green"], 50)


if __name__ == "__main__":
    unittest.main()
