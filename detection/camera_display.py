"""
detection/camera_display.py
============================
Mở camera (hoặc video file) và hiển thị thời gian đèn xanh (green time)
được tính từ TrafficLightOptimizer lên trên khung hình.

Chạy:
    python detection/camera_display.py              # dùng webcam (index 0)
    python detection/camera_display.py --video video_data/traffictrim.mp4
    python detection/camera_display.py --cam 0

Phím tắt:
    Q / ESC  → thoát
    SPACE    → tạm dừng / tiếp tục
"""

import os
import sys
import time
import datetime
import argparse
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path.insert(0, ROOT_DIR)

import cv2

# ---------------------------------------------------------------------------
# Import TrafficLightOptimizer (fallback về rule-based nếu ML không có)
# ---------------------------------------------------------------------------
try:
    sys.path.insert(0, os.path.join(ROOT_DIR, "integration_system"))
    from integration_system.system_runner import (
        TrafficLightOptimizer,
        CongestionClassifier,
        CAMERA_PHASE_MAP,
        CAMERA_BASELINE,
    )
    _OPTIMIZER_AVAILABLE = True
except Exception as _e:
    print(f"[WARN] Không import được optimizer: {_e}. Dùng rule-based đơn giản.")
    _OPTIMIZER_AVAILABLE = False


# ---------------------------------------------------------------------------
# Fallback thuần nếu import lỗi
# ---------------------------------------------------------------------------
class _SimpleOptimizer:
    _RULE = {"low": 20, "medium": 40, "high": 60, "severe": 90}

    def optimize(self, congestion_level: str) -> dict:
        gt = self._RULE.get(str(congestion_level).lower(), 40)
        return {"green_time": gt, "mode": "rule", "phase": "—", "delta": 0.0, "baseline": gt}

    def optimize_with_ml(self, **kw) -> dict:
        return self.optimize(kw.get("congestion_level", "medium"))


class _SimpleClassifier:
    def classify(self, count: int) -> str:
        if count < 15:   return "low"
        if count < 30:   return "medium"
        if count < 50:   return "high"
        return "severe"


# ---------------------------------------------------------------------------
# Màu sắc & font
# ---------------------------------------------------------------------------
_FONT       = cv2.FONT_HERSHEY_DUPLEX
_FONT_SMALL = cv2.FONT_HERSHEY_SIMPLEX

_COLOR_GREEN  = (50,  220,  80)
_COLOR_YELLOW = (30,  210, 220)
_COLOR_RED    = (50,   60, 220)
_COLOR_WHITE  = (240, 240, 240)
_COLOR_DARK   = (20,   20,  20)
_COLOR_PANEL  = (30,   30,  30)

_CONGESTION_COLOR = {
    "low":    (50, 200, 80),
    "medium": (30, 190, 230),
    "high":   (30, 100, 230),
    "severe": (40,  40, 210),
}

# ---------------------------------------------------------------------------
# Vẽ HUD (Heads-Up Display)
# ---------------------------------------------------------------------------

def _draw_rounded_rect(img, x1, y1, x2, y2, color, alpha=0.55, radius=12):
    """Vẽ hình chữ nhật bo góc mờ (overlay)."""
    overlay = img.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    # Viền mỏng
    cv2.rectangle(img, (x1, y1), (x2, y2), tuple(min(c + 60, 255) for c in color), 1)


def draw_hud(frame, green_time: float, congestion: str, mode: str,
             phase: str, delta: float, baseline: float,
             vehicle_count: int, fps_actual: float, paused: bool):
    h, w = frame.shape[:2]

    # === Panel chính — góc trái trên ===
    panel_x1, panel_y1 = 10, 10
    panel_x2, panel_y2 = 340, 230
    _draw_rounded_rect(frame, panel_x1, panel_y1, panel_x2, panel_y2,
                       _COLOR_PANEL, alpha=0.65)

    # Tiêu đề
    cv2.putText(frame, "TRAFFIC LIGHT MONITOR",
                (panel_x1 + 12, panel_y1 + 28),
                _FONT_SMALL, 0.55, _COLOR_WHITE, 1, cv2.LINE_AA)

    # Đường kẻ ngang
    cv2.line(frame, (panel_x1 + 10, panel_y1 + 34),
             (panel_x2 - 10, panel_y1 + 34), (80, 80, 80), 1)

    # GREEN TIME — to và nổi bật
    gt_color = _COLOR_GREEN if green_time >= 30 else _COLOR_YELLOW if green_time >= 15 else _COLOR_RED
    cv2.putText(frame, f"{green_time:.1f}s",
                (panel_x1 + 12, panel_y1 + 85),
                _FONT, 1.5, gt_color, 2, cv2.LINE_AA)
    cv2.putText(frame, "GREEN TIME",
                (panel_x1 + 12, panel_y1 + 105),
                _FONT_SMALL, 0.42, (160, 160, 160), 1, cv2.LINE_AA)

    # Delta
    delta_str = f"{delta:+.1f}s" if delta != 0 else "±0s"
    delta_col = _COLOR_GREEN if delta > 0 else _COLOR_RED if delta < 0 else _COLOR_WHITE
    cv2.putText(frame, f"Delta: {delta_str}  Base: {baseline:.0f}s",
                (panel_x1 + 12, panel_y1 + 130),
                _FONT_SMALL, 0.45, delta_col, 1, cv2.LINE_AA)

    # Congestion
    cng_col = _CONGESTION_COLOR.get(congestion.lower(), _COLOR_WHITE)
    cv2.putText(frame, f"Congestion: {congestion.upper()}",
                (panel_x1 + 12, panel_y1 + 158),
                _FONT_SMALL, 0.50, cng_col, 1, cv2.LINE_AA)

    # Phase & Mode
    cv2.putText(frame, f"Phase: {phase}   Mode: {mode}",
                (panel_x1 + 12, panel_y1 + 182),
                _FONT_SMALL, 0.42, (150, 150, 150), 1, cv2.LINE_AA)

    # Vehicles
    cv2.putText(frame, f"Vehicles: {vehicle_count}   FPS: {fps_actual:.1f}",
                (panel_x1 + 12, panel_y1 + 207),
                _FONT_SMALL, 0.42, (150, 150, 150), 1, cv2.LINE_AA)

    # === Đồng hồ thực — góc phải trên ===
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    date_str = datetime.datetime.now().strftime("%d/%m/%Y")
    (tw, _), _ = cv2.getTextSize(now_str, _FONT, 0.85, 2)
    clock_x = w - tw - 20
    _draw_rounded_rect(frame, clock_x - 10, 10, w - 8, 75, _COLOR_PANEL, alpha=0.60)
    cv2.putText(frame, now_str,
                (clock_x, 48),
                _FONT, 0.85, _COLOR_WHITE, 2, cv2.LINE_AA)
    cv2.putText(frame, date_str,
                (clock_x + 5, 68),
                _FONT_SMALL, 0.40, (160, 160, 160), 1, cv2.LINE_AA)

    # === Đèn tín hiệu mini — góc phải dưới ===
    _draw_traffic_light(frame, w - 70, h - 175, green_time)

    # === Thông báo PAUSED ===
    if paused:
        (pw, ph), _ = cv2.getTextSize("  PAUSED  ", _FONT, 1.2, 3)
        px = (w - pw) // 2
        py = h // 2
        _draw_rounded_rect(frame, px - 15, py - 45, px + pw + 15, py + 20,
                           (0, 0, 0), alpha=0.7)
        cv2.putText(frame, "  PAUSED  ", (px, py),
                    _FONT, 1.2, _COLOR_YELLOW, 3, cv2.LINE_AA)


def _draw_traffic_light(frame, x: int, y: int, green_time: float):
    """Vẽ đèn tín hiệu thu nhỏ."""
    # Hộp đèn
    _draw_rounded_rect(frame, x - 20, y - 5, x + 55, y + 155, (30, 30, 30), alpha=0.75)

    # Ba bóng đèn
    positions = [y + 25, y + 75, y + 125]
    colors_off = [(30, 30, 80), (30, 80, 80), (30, 80, 30)]
    # Đèn nào sáng?
    if green_time >= 30:
        on_idx = 2    # xanh
    elif green_time >= 15:
        on_idx = 1    # vàng
    else:
        on_idx = 0    # đỏ

    colors_on = [
        (50,  60, 230),   # đỏ
        (30, 210, 230),   # vàng
        (50, 220, 60),    # xanh
    ]

    for i, cy in enumerate(positions):
        col = colors_on[i] if i == on_idx else colors_off[i]
        cv2.circle(frame, (x + 17, cy), 18, col, -1)
        if i == on_idx:
            cv2.circle(frame, (x + 17, cy), 18, tuple(min(c + 80, 255) for c in col), 2)


# ---------------------------------------------------------------------------
# Giả lập số xe (trong trường hợp không có detector thật)
# ---------------------------------------------------------------------------

class _FakeVehicleCounter:
    """Giả lập đếm xe theo thời gian để demo."""
    def __init__(self):
        self._count = 12
        self._next_change = time.time() + 8.0

    def get_count(self) -> int:
        now = time.time()
        if now >= self._next_change:
            # Dao động ngẫu nhiên ±5 xe, giới hạn 0–70
            self._count = max(0, min(70, self._count + random.randint(-5, 7)))
            self._next_change = now + random.uniform(5.0, 12.0)
        return self._count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Camera display với overlay thời gian đèn")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--video", metavar="PATH",
                   default=os.path.join(ROOT_DIR, "video_data", "traffic1.mp4"), # Thêm video mặc định
                   help="Đường dẫn tới file video (mặc định: video_data/traffic1.mp4)")
    g.add_argument("--cam",   metavar="INDEX", type=int,
                   help="Index webcam (0, 1, ...)")
    p.add_argument("--camera-id", default="CAM_01",
                   help="Camera ID cho optimizer (mặc định: CAM_01)")
    p.add_argument("--update-interval", type=float, default=5.0,
                   help="Tần suất cập nhật green_time (giây, mặc định: 5)")
    return p.parse_args()


def main():
    args = parse_args()

    # --- Chọn source ---
    if args.cam is not None:
        source = args.cam
        source_label = f"Webcam #{args.cam}"
    else:
        source = args.video
        source_label = os.path.basename(str(source))

    print(f"[camera_display] Opening source: {source_label}")
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open source: {source}")
        sys.exit(1)

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # --- Optimizer ---
    if _OPTIMIZER_AVAILABLE:
        optimizer   = TrafficLightOptimizer()
        classifier  = CongestionClassifier()
    else:
        optimizer   = _SimpleOptimizer()
        classifier  = _SimpleClassifier()

    camera_id = args.camera_id

    # --- Fake counter (không cần model YOLO để demo) ---
    fake_counter = _FakeVehicleCounter()

    # --- State ---
    green_time     = 40.0
    congestion     = "medium"
    mode           = "rule"
    phase          = "—"
    delta          = 0.0
    baseline       = float(CAMERA_BASELINE.get(camera_id, 30) if _OPTIMIZER_AVAILABLE else 30)
    vehicle_count  = 0

    last_update    = 0.0
    paused         = False

    fps_counter    = 0
    fps_timer      = time.time()
    fps_actual     = 0.0

    window_name = "Traffic Camera — Green Time Monitor"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1024, 600)

    print("[camera_display] Started. Press Q/ESC to quit, SPACE to pause.")

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                # Video ended -> rewind
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

        # --- Cập nhật green_time theo chu kỳ ---
        now = time.time()
        if now - last_update >= args.update_interval:  # noqa
            last_update    = now
            vehicle_count  = fake_counter.get_count()
            congestion     = classifier.classify(vehicle_count)
            now_dt         = datetime.datetime.now()

            try:
                result = optimizer.optimize_with_ml(
                    camera_id=camera_id,
                    queue_proxy=float(vehicle_count * 0.6),
                    inbound_count=vehicle_count,
                    congestion_level=congestion,
                    hour=now_dt.hour,
                    dow=now_dt.weekday(),
                )
            except TypeError:
                # _SimpleOptimizer không có keyword args chi tiết
                result = optimizer.optimize(congestion)

            green_time = float(result.get("green_time", 40))
            mode       = str(result.get("mode",       "rule"))
            phase      = str(result.get("phase",      "—"))
            delta      = float(result.get("delta",    0.0))
            baseline   = float(result.get("baseline", 30))

            print(
                f"[Update] Vehicles={vehicle_count} | Congestion={congestion} | "
                f"GreenTime={green_time:.1f}s | Delta={delta:+.1f}s | Mode={mode}"
            )

        # --- FPS thực ---
        fps_counter += 1
        if now - fps_timer >= 1.0:
            fps_actual  = fps_counter / (now - fps_timer)
            fps_counter = 0
            fps_timer   = now

        # --- Vẽ HUD lên frame ---
        display = frame.copy()
        draw_hud(
            display,
            green_time=green_time,
            congestion=congestion,
            mode=mode,
            phase=phase,
            delta=delta,
            baseline=baseline,
            vehicle_count=vehicle_count,
            fps_actual=fps_actual,
            paused=paused,
        )

        cv2.imshow(window_name, display)

        # --- Phím tắt ---
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q"), 27):   # Q hoặc ESC
            break
        elif key == ord(" "):                  # SPACE
            paused = not paused

    cap.release()
    cv2.destroyAllWindows()
    print("[camera_display] Exited.")


if __name__ == "__main__":
    main()
