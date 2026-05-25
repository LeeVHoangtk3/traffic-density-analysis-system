"""Adapter from the integration runner to the ML traffic-light optimizer."""

from __future__ import annotations

import datetime as dt
import os
from typing import Any

import pandas as pd

from ml_service.phase_optimizer import PhaseLightOptimizer


class LightDeltaModel:
    """Bridge three XGBoost predictors into a single predict_delta() API."""

    MODEL_FILES = {
        "straight": "model_straight.pkl",
        "left": "model_left.pkl",
        "right": "model_right.pkl",
    }

    PHASE_2_DIRECTIONS = {"left", "turn_left", "phase_2", "left_turn"}

    def __init__(self, model_dir: str | None = None) -> None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_dir = model_dir or os.path.join(base_dir, "model")
        self.predictors: dict[str, Any] = {}
        self.optimizer = PhaseLightOptimizer()
        self._loaded = False
        self._fallback_reason: str | None = None

    def _load(self) -> None:
        """Lazy-load all direction models once."""
        if self._loaded:
            return

        try:
            from ml_service.traffic_predictor import TrafficPredictor
        except Exception as exc:
            self.predictors = {}
            self._fallback_reason = f"TrafficPredictor unavailable: {exc}"
            self._loaded = True
            return

        loaded: dict[str, Any] = {}
        missing: list[str] = []
        for direction, filename in self.MODEL_FILES.items():
            model_path = os.path.join(self.model_dir, filename)
            predictor = TrafficPredictor(model_path=model_path)
            if not predictor.load_model():
                missing.append(model_path)
                continue
            loaded[direction] = predictor

        if missing:
            self.predictors = {}
            self._fallback_reason = "Missing traffic model file(s): " + ", ".join(missing)
            self._loaded = True
            return

        self.predictors = loaded
        self._loaded = True

    def predict_delta(self, feature_dict: dict[str, Any]) -> float:
        """Return the optimized green-time delta for the requested phase."""
        self._load()

        predictions = self._predict_direction_counts(feature_dict)

        plan = self.optimizer.optimize(
            predicted_straight=predictions["straight"],
            predicted_left=predictions["left"],
            predicted_right=predictions["right"],
        )

        return self._delta_for_runner(feature_dict, plan)

    def prediction_source(self) -> str:
        """Return the active prediction source for runtime diagnostics."""
        self._load()
        return "xgboost" if self.predictors else "heuristic_fallback"

    @property
    def fallback_reason(self) -> str | None:
        self._load()
        return self._fallback_reason

    def predict_plan(self, feature_dict: dict[str, Any]) -> dict[str, Any]:
        """Return the full optimizer plan plus raw predictions for diagnostics."""
        self._load()
        predictions = self._predict_direction_counts(feature_dict)
        plan = self.optimizer.optimize(
            predicted_straight=predictions["straight"],
            predicted_left=predictions["left"],
            predicted_right=predictions["right"],
        )
        plan["predicted_straight"] = predictions["straight"]
        plan["predicted_left"] = predictions["left"]
        plan["predicted_right"] = predictions["right"]
        plan["selected_phase"] = self._resolve_phase_key(feature_dict)
        plan["prediction_source"] = "xgboost" if self.predictors else "heuristic_fallback"
        if self._fallback_reason:
            plan["fallback_reason"] = self._fallback_reason
        return plan

    def _predict_direction_counts(self, feature_dict: dict[str, Any]) -> dict[str, int]:
        if self.predictors:
            return {
                direction: int(predictor.predict(self._build_history(feature_dict, direction)))
                for direction, predictor in self.predictors.items()
            }

        return {
            direction: max(0, int(round(self._directional_history_counts(feature_dict, direction)[-1])))
            for direction in self.MODEL_FILES
        }

    def _delta_for_runner(
        self,
        feature_dict: dict[str, Any],
        plan: dict[str, float | int],
    ) -> float:
        phase_key = self._resolve_phase_key(feature_dict)
        baseline_green = float(feature_dict.get("baseline_green", 30) or 30)
        if phase_key == "phase_2":
            target_green = float(plan["phase_2_green"])
        else:
            target_green = float(plan["phase_1_green"])
        return target_green - baseline_green

    def _build_history(self, feature_dict: dict[str, Any], direction: str) -> pd.DataFrame:
        target_time = self._target_time(feature_dict)
        last_time = target_time - dt.timedelta(minutes=15)
        counts = self._directional_history_counts(feature_dict, direction)

        rows = []
        for idx, count in enumerate(counts):
            rows.append(
                {
                    "timestamp": last_time - dt.timedelta(minutes=15 * (len(counts) - 1 - idx)),
                    "segment_id": self._segment_id(feature_dict),
                    "vehicle_count": max(0, int(round(count))),
                }
            )
        return pd.DataFrame(rows)

    def _directional_history_counts(
        self,
        feature_dict: dict[str, Any],
        direction: str,
    ) -> list[float]:
        inbound = max(0.0, float(feature_dict.get("inbound_count", 0.0) or 0.0))
        queue_proxy = max(0.0, float(feature_dict.get("queue_proxy", 0.0) or 0.0))
        level = str(feature_dict.get("congestion_level", "medium")).lower()

        level_boost = {
            "low": 0.85,
            "medium": 1.0,
            "high": 1.18,
            "heavy": 1.35,
            "severe": 1.35,
        }.get(level, 1.0)

        direction_weights = {
            "straight": 0.62,
            "left": 0.25,
            "right": 0.13,
        }
        base = inbound * direction_weights[direction] * level_boost
        base += queue_proxy * self._queue_weight(direction)

        return [base * factor for factor in (0.72, 0.84, 0.94, 1.0, 1.08)]

    @staticmethod
    def _queue_weight(direction: str) -> float:
        return {"straight": 0.75, "left": 1.05, "right": 0.45}[direction]

    @staticmethod
    def _segment_id(feature_dict: dict[str, Any]) -> int:
        raw_segment = feature_dict.get("segment_id", 138)
        try:
            return int(raw_segment)
        except (TypeError, ValueError):
            return 138

    @staticmethod
    def _target_time(feature_dict: dict[str, Any]) -> dt.datetime:
        now = dt.datetime.now().replace(second=0, microsecond=0)
        hour = int(feature_dict.get("hour", now.hour) or 0) % 24
        dow = int(feature_dict.get("day_of_week", now.weekday()) or 0) % 7

        monday = dt.datetime(2026, 1, 5, hour, 0)
        return monday + dt.timedelta(days=dow)

    def _resolve_phase_key(self, feature_dict: dict[str, Any]) -> str:
        explicit = str(
            feature_dict.get("phase")
            or feature_dict.get("controlled_phase")
            or feature_dict.get("direction")
            or ""
        ).lower()
        if explicit == "phase_1":
            return "phase_1"
        if explicit in self.PHASE_2_DIRECTIONS:
            return "phase_2"

        camera_id = str(feature_dict.get("camera_id", "CAM_01")).upper()
        if camera_id in {"CAM_LEFT", "CAM_PHASE_2"}:
            return "phase_2"

        return "phase_1"


if __name__ == "__main__":
    model = LightDeltaModel()
    sample = {
        "camera_id": "CAM_01",
        "queue_proxy": 12.0,
        "inbound_count": 80,
        "congestion_level": "high",
        "baseline_green": 30,
        "hour": 8,
        "day_of_week": 1,
    }
    print(model.predict_plan(sample))
