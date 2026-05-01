"""Quick smoke-test for system_runner components."""
import sys, os
sys.path.insert(0, ".")

from integration_system.system_runner import (
    CongestionClassifier, TrafficLightOptimizer,
    PerformanceMonitor, get_phase,
    CAMERA_PHASE_MAP,
)

PASS = 0
FAIL = 0

def check(label, condition):
    global PASS, FAIL
    if condition:
        print(f"  [PASS] {label}")
        PASS += 1
    else:
        print(f"  [FAIL] {label}")
        FAIL += 1

print()
print("=== [1] CongestionClassifier ===")
clf = CongestionClassifier()
for count, expected in [(5, "low"), (20, "medium"), (40, "high"), (60, "severe")]:
    result = clf.classify(count)
    check(f"count={count} -> {result}", result == expected)

print()
print("=== [2] DirectionRouter ===")
for cam in CAMERA_PHASE_MAP:
    info = get_phase(cam)
    check(f"{cam} has phase", "phase" in info and "direction" in info)

print()
print("=== [3] TrafficLightOptimizer (rule-based) ===")
opt = TrafficLightOptimizer()
for level, expected_gt in [("low", 20), ("medium", 40), ("high", 60), ("severe", 90)]:
    r = opt.optimize(level)
    check(f"rule '{level}' -> {r['green_time']}s", r["green_time"] == expected_gt)

print()
print("=== [4] TrafficLightOptimizer (ML-based) ===")
cases = [
    ("CAM_01", 18.0, 60, "high",    8, 1),
    ("CAM_02",  2.0, 10, "low",    14, 5),
    ("CAM_03", -5.0, 20, "medium", 22, 6),
]
for cam, qp, ic, cl, hr, dw in cases:
    r = opt.optimize_with_ml(cam, qp, ic, cl, hr, dw)
    check(
        f"{cam} | phase={r['phase']} | green={r['green_time']}s | delta={r['delta']:+.2f}s | mode={r['mode']}",
        r["green_time"] > 0 and r["mode"] in ("ml", "rule_fallback")
    )

print()
print("=== [5] PerformanceMonitor ===")
mon = PerformanceMonitor()
perf = mon.monitor()
check(f"CPU={perf['cpu_usage']}%  RAM={perf['memory_usage']}%", "cpu_usage" in perf)

print()
print(f"{'='*40}")
print(f"  RESULT: {PASS} passed / {FAIL} failed")
print(f"{'='*40}")
