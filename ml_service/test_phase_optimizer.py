import unittest

from ml_service.phase_optimizer import PhaseLightOptimizer


class PhaseLightOptimizerTest(unittest.TestCase):
    def setUp(self):
        self.optimizer = PhaseLightOptimizer()

    def assert_safe_plan(self, result):
        self.assertEqual(result["phase_1_green"] + result["phase_2_green"], 80)
        self.assertGreaterEqual(result["phase_1_green"], 15)
        self.assertLessEqual(result["phase_1_green"], 55)
        self.assertGreaterEqual(result["phase_2_green"], 15)
        self.assertLessEqual(result["phase_2_green"], 55)

    def test_heavy_straight_flow_hits_phase_1_cap(self):
        result = self.optimizer.optimize(
            predicted_straight=500,
            predicted_left=1,
            predicted_right=50,
        )
        self.assert_safe_plan(result)
        self.assertEqual(result["phase_1_green"], 55)
        self.assertEqual(result["phase_2_green"], 25)
        self.assertEqual(result["delta_phase_1"], 5)
        self.assertEqual(result["delta_phase_2"], -5)

    def test_heavy_left_flow_hits_phase_2_cap(self):
        result = self.optimizer.optimize(
            predicted_straight=1,
            predicted_left=500,
            predicted_right=1,
        )
        self.assert_safe_plan(result)
        self.assertEqual(result["phase_1_green"], 25)
        self.assertEqual(result["phase_2_green"], 55)
        self.assertEqual(result["delta_phase_1"], -25)
        self.assertEqual(result["delta_phase_2"], 25)

    def test_zero_flow_returns_baseline(self):
        result = self.optimizer.optimize(0, 0, 0)
        self.assert_safe_plan(result)
        self.assertEqual(result["phase_1_green"], 50)
        self.assertEqual(result["phase_2_green"], 30)
        self.assertEqual(result["delta_phase_1"], 0)
        self.assertEqual(result["delta_phase_2"], 0)

    def test_negative_predictions_are_clamped(self):
        result = self.optimizer.optimize(-10, -5, -1)
        self.assert_safe_plan(result)
        self.assertEqual(result["phase_1_green"], 50)
        self.assertEqual(result["phase_2_green"], 30)

    def test_balanced_pressure_stays_inside_limits(self):
        result = self.optimizer.optimize(70, 45, 20)
        self.assert_safe_plan(result)
        self.assertTrue(25 <= result["phase_1_green"] <= 55)
        self.assertTrue(25 <= result["phase_2_green"] <= 55)


if __name__ == "__main__":
    unittest.main()
