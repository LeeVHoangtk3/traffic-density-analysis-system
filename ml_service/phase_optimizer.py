"""Two-phase adaptive green-time optimizer.

The optimizer converts predicted traffic volume for three directions into a
safe 2-phase signal plan:

- Phase 1: straight + right
- Phase 2: left

Only the 80 seconds of green time in a 90-second cycle are allocated here. The
remaining 10 seconds are reserved by the signal controller for transitions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhaseOptimizationResult:
    phase_1_green: int
    phase_2_green: int
    delta_phase_1: int
    delta_phase_2: int
    pressure_phase_1: float
    pressure_phase_2: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "phase_1_green": self.phase_1_green,
            "phase_2_green": self.phase_2_green,
            "delta_phase_1": self.delta_phase_1,
            "delta_phase_2": self.delta_phase_2,
            "pressure_phase_1": self.pressure_phase_1,
            "pressure_phase_2": self.pressure_phase_2,
        }


class PhaseLightOptimizer:
    """Allocate green time with hard safety constraints."""

    def __init__(
        self,
        total_green: int = 80,
        phase_1_baseline: int = 50,
        phase_2_baseline: int = 30,
        min_green: int = 15,
        max_green: int = 55,
        right_weight: float = 0.3,
        left_weight: float = 1.5,
    ) -> None:
        if phase_1_baseline + phase_2_baseline != total_green:
            raise ValueError("Phase baselines must sum to total_green.")
        if min_green * 2 > total_green:
            raise ValueError("min_green is too high for a two-phase cycle.")
        if max_green * 2 < total_green:
            raise ValueError("max_green is too low for a two-phase cycle.")

        self.total_green = int(total_green)
        self.phase_1_baseline = int(phase_1_baseline)
        self.phase_2_baseline = int(phase_2_baseline)
        self.min_green = int(min_green)
        self.max_green = int(max_green)
        self.right_weight = float(right_weight)
        self.left_weight = float(left_weight)

        # Because phase_2 is derived as total_green - phase_1, phase_1 must be
        # kept inside this tighter interval so both phases stay valid.
        self._phase_1_min = max(self.min_green, self.total_green - self.max_green)
        self._phase_1_max = min(self.max_green, self.total_green - self.min_green)

    def optimize(
        self,
        predicted_straight: float,
        predicted_left: float,
        predicted_right: float,
    ) -> dict[str, float | int]:
        """Return optimized green seconds and deltas for the two phases."""

        straight = max(0.0, float(predicted_straight))
        left = max(0.0, float(predicted_left))
        right = max(0.0, float(predicted_right))

        pressure_phase_1 = straight + self.right_weight * right
        pressure_phase_2 = self.left_weight * left
        total_pressure = pressure_phase_1 + pressure_phase_2

        if total_pressure <= 0:
            phase_1_green = self.phase_1_baseline
        else:
            raw_phase_1 = pressure_phase_1 / total_pressure * self.total_green
            clamped_phase_1 = max(self._phase_1_min, min(self._phase_1_max, raw_phase_1))
            phase_1_green = int(round(clamped_phase_1))

        phase_1_green = max(self._phase_1_min, min(self._phase_1_max, phase_1_green))
        phase_2_green = self.total_green - phase_1_green

        result = PhaseOptimizationResult(
            phase_1_green=phase_1_green,
            phase_2_green=phase_2_green,
            delta_phase_1=phase_1_green - self.phase_1_baseline,
            delta_phase_2=phase_2_green - self.phase_2_baseline,
            pressure_phase_1=round(pressure_phase_1, 4),
            pressure_phase_2=round(pressure_phase_2, 4),
        )
        return result.to_dict()


if __name__ == "__main__":
    optimizer = PhaseLightOptimizer()
    print(optimizer.optimize(80, 20, 15))
