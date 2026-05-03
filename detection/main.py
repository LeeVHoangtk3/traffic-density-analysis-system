"""
detection/main.py  —  Module A: Vehicle Detection & Tracking  (V5 Fixed)

Tổng hợp tối ưu từ V2 + V4 + V5, đã fix:
  - [F1] Async mode double counting: _process_tracks chỉ chạy với tracks MỚI
  - [F2] frame.copy() → resize trước khi đưa vào queue, giảm memory
  - [F3] dry_run_ref [0] anti-pattern → dùng class EventCounter
  - [F4] display_in_notebook dùng src URL thay vì base64 nếu file nhỏ

Cách chạy:
  python -m detection.main                          # sync, hiển thị cửa sổ
  SYNC_MODE=false python -m detection.main          # async, video mượt
  NO_DISPLAY=true python -m detection.main          # headless
  PLAYBACK_SPEED=0.5 python -m detection.main       # chậm 2x (SYNC_MODE=false)
  ALERT_LOG=alerts.csv python -m detection.main     # ghi spike/HIGH ra CSV
  DRY_RUN=true python -m detection.main             # không gửi HTTP
"""
from __future__ import annotations

import csv
import os
import sys
import threading
import time
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(BASE_DIR))
sys.path.append(BASE_DIR)

import cv2
import json
import torch
import requests

from .camera_engine import CameraEngine
from .engine.frame_processor import FrameProcessor
from .engine.detector import Detector
from .engine.tracker import Tracker
from .engine.counter import VehicleCounter
from .engine.density_estimator import DensityEstimator
from .engine.zone_manager import ZoneManager
from .engine.event_generator import EventGenerator
from .integration.publisher import EventPublisher


# ── Môi trường ────────────────────────────────────────────────────────────────
def _is_notebook() -> bool:
    try:
        from IPython import get_ipython
        return get_ipython() is not None
    except ImportError:
        return False

IS_NOTEBOOK = _is_notebook()
IS_COLAB    = "COLAB_GPU" in os.environ
HAS_CUDA    = torch.cuda.is_available()


# ── Cấu hình ──────────────────────────────────────────────────────────────────
API_URL      = os.getenv("TRAFFIC_API_URL",     "http://127.0.0.1:8000/detection")
VIDEO_SOURCE = os.getenv("TRAFFIC_VIDEO_SOURCE", str(Path(BASE_DIR) / "video_data" / "traffic1.mp4"))
MODEL_PATH   = os.getenv("TRAFFIC_MODEL_PATH",   str(Path(BASE_DIR) / "detection" / "pro_models" / "yolov9_img960_ultimate.pt"))
OUTPUT_VIDEO = os.getenv("TRAFFIC_OUTPUT_VIDEO", "output_v5.mp4")
ALERT_LOG    = os.getenv("ALERT_LOG", "")

CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.40"))
TARGET_WIDTH   = 960  # cố định — model train imgsz=960

SYNC_MODE      = os.getenv("SYNC_MODE", "true").lower() in ("1", "true", "yes")
NO_DISPLAY     = os.getenv("NO_DISPLAY", "false").lower() in ("1", "true", "yes")
PLAYBACK_SPEED = float(os.getenv("PLAYBACK_SPEED", "1.0"))
DRY_RUN        = os.getenv("DRY_RUN", "false").lower() in ("1", "true", "yes")

AGGREGATION_INTERVAL_SEC = 15 * 60

FRAME_SKIP_BY_DENSITY: dict[str, int] = {
    "LOW":    5 if HAS_CUDA else 10,
    "MEDIUM": 3 if HAS_CUDA else 6,
    "HIGH":   1 if HAS_CUDA else 2,
}


# ── F3: EventCounter thay thế dry_run_ref=[0] anti-pattern ───────────────────
class EventCounter:
    """Đếm event được generate — dùng nonlocal thay vì list hack."""
    def __init__(self):
        self.total = 0

    def increment(self):
        self.total += 1


# ── AlertLogger ───────────────────────────────────────────────────────────────
class AlertLogger:
    """Log spike và HIGH density ra CSV."""

    _FIELDS = ["timestamp", "frame_idx", "video_sec", "density",
               "vehicle_count", "prev_count", "spike_ratio", "event_type"]

    def __init__(self, csv_path: str = "") -> None:
        self._file   = None
        self._writer = None
        self.counts: dict[str, int] = {}
        if csv_path:
            p = Path(csv_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            self._file   = open(p, "w", newline="", encoding="utf-8")
            self._writer = csv.DictWriter(self._file, fieldnames=self._FIELDS)
            self._writer.writeheader()
            print(f"[AlertLogger] → {csv_path}")

    def log(self, frame_idx: int, video_sec: float, density: str,
            vehicle_count: int, prev_count: int, event_type: str) -> None:
        self.counts[event_type] = self.counts.get(event_type, 0) + 1
        ratio = vehicle_count / max(prev_count, 1)
        print(f"[ALERT] {event_type.upper():12s} | f={frame_idx:5d} "
              f"| {density:6s} | count={vehicle_count} | ratio={ratio:.2f}x")
        if self._writer:
            self._writer.writerow({
                "timestamp":     time.strftime("%Y-%m-%d %H:%M:%S"),
                "frame_idx":     frame_idx,
                "video_sec":     f"{video_sec:.1f}",
                "density":       density,
                "vehicle_count": vehicle_count,
                "prev_count":    prev_count,
                "spike_ratio":   f"{ratio:.3f}",
                "event_type":    event_type,
            })

    def summary(self) -> str:
        return " | ".join(f"{v} {k}" for k, v in self.counts.items()) or "none"

    def close(self) -> None:
        if self._file:
            self._file.close()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _trigger_aggregation(api_url: str, camera_id: str) -> None:
    try:
        base = api_url.rsplit("/", 1)[0] if "/" in api_url else api_url
        r = requests.post(f"{base}/aggregation/compute",
                          params={"camera_id": camera_id}, timeout=5)
        if r.status_code == 200:
            d = r.json()
            print(f"[Aggregation] {d['vehicle_count']} xe | {d['congestion_level']}")
        else:
            print(f"[Aggregation] HTTP {r.status_code}")
    except Exception as e:
        print(f"[Aggregation] Lỗi: {e}")


def _get_output_size(source: str, target_w: int) -> tuple[int, int]:
    src = int(source) if str(source).isdigit() else source
    cap = cv2.VideoCapture(src)
    w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if w == 0 or h == 0:
        return target_w, target_w
    return target_w, int(h * target_w / w)


def _process_tracks(
    tracks: list,
    zone_manager: ZoneManager,
    counter: VehicleCounter,
    event_generator: EventGenerator,
    publisher: EventPublisher,
    camera_id: str,
    event_counter: EventCounter,
) -> dict:
    """
    Zone crossing → counter → publish event.
    Trả về totals mới nếu có crossing, {} nếu không.

    F1 FIX: hàm này CHỈ được gọi khi tracks là MỚI (new_tracks is not None)
    → không bao giờ process lại last_tracks cũ → tránh double counting
    """
    totals = {}
    for t in tracks:
        x1, y1, x2, y2 = t["bbox"]
        cx       = (x1 + x2) // 2
        cy_bottom = y2  # điểm tiếp đất — chính xác hơn center
        zone_dir = zone_manager.check_crossing(t["track_id"], cx, cy_bottom)
        if zone_dir:
            counter.count(t["class_name"])
            totals = counter.get_totals()
            event  = event_generator.generate(
                camera_id=camera_id, track=t, direction=zone_dir)
            if DRY_RUN:
                event_counter.increment()  # F3: không dùng list hack
            else:
                publisher.publish(event)
    return totals


def _draw_hud(frame, smoothed_fps: float, density: str, track_count: int,
              spike: bool, next_skip: int, cached_totals: dict) -> None:
    hud = (f"FPS:{smoothed_fps:.1f} | Density:{density} | "
           f"Tracks:{track_count} | Spike:{'YES' if spike else 'no'}")
    if not SYNC_MODE:
        hud += f" | Skip:{next_skip}"
    cv2.rectangle(frame, (8, 8), (720, 34), (20, 20, 20), -1)
    cv2.putText(frame, hud, (14, 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)
    y = 50
    for vtype, cnt in cached_totals.items():
        cv2.putText(frame, f"{vtype}: {cnt}", (14, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, (180, 255, 180), 1, cv2.LINE_AA)
        y += 24


def display_in_notebook(video_path: str) -> None:
    """
    F4 FIX: Dùng file path URL thay vì base64 encode toàn bộ video.
    Base64 với video dài (~100MB) sẽ làm notebook treo.
    Fallback sang base64 chỉ khi file < 20MB.
    """
    from IPython.display import HTML, display as ipy_display
    size_mb = Path(video_path).stat().st_size / 1024 / 1024

    if size_mb < 20:
        # File nhỏ — embed base64 thẳng vào cell
        import base64
        data = base64.b64encode(Path(video_path).read_bytes()).decode()
        src  = f"data:video/mp4;base64,{data}"
    else:
        # File lớn — dùng đường dẫn tương đối
        # Jupyter VS Code serve file từ workspace root
        src = video_path
        print(f"[Info] Video lớn ({size_mb:.1f}MB) — dùng file path thay vì base64")

    ipy_display(HTML(
        f'<video width="960" controls autoplay loop style="max-width:100%">'
        f'<source src="{src}" type="video/mp4"></video>'
    ))
    print(f"[Info] Video: {video_path} ({size_mb:.1f} MB)")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    camera_id   = "CAM_01"
    config_path = os.path.join(BASE_DIR, "detection", "configs_cameras", f"{camera_id.lower()}.json")

    for path, label in [(config_path, "Camera config"), (MODEL_PATH, "YOLO model")]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"{label} not found: {path}")
    if (isinstance(VIDEO_SOURCE, str) and not VIDEO_SOURCE.isdigit()
            and not os.path.exists(VIDEO_SOURCE)):
        raise FileNotFoundError(f"Video source not found: {VIDEO_SOURCE}")

    with open(config_path, encoding="utf-8") as f:
        camera_config = json.load(f)

    # ── Init ──────────────────────────────────────────────────────────────────
    camera            = CameraEngine(VIDEO_SOURCE)
    processor         = FrameProcessor(target_width=TARGET_WIDTH)
    detector          = Detector(MODEL_PATH, conf_threshold=CONF_THRESHOLD, img_size=TARGET_WIDTH)
    tracker           = Tracker()
    counter           = VehicleCounter()
    density_estimator = DensityEstimator(window=30)
    event_generator   = EventGenerator()
    publisher         = EventPublisher(API_URL)
    zone_manager      = ZoneManager(camera_config["zones"])
    alert_logger      = AlertLogger(csv_path=ALERT_LOG)
    event_counter     = EventCounter()  # F3

    fps = camera.get_fps()
    if fps <= 0:
        fps = 30.0
    frame_delay = 1.0 / (fps * PLAYBACK_SPEED)

    out_w, out_h = _get_output_size(VIDEO_SOURCE, TARGET_WIDTH)
    out = cv2.VideoWriter(OUTPUT_VIDEO, cv2.VideoWriter_fourcc(*"mp4v"),
                          fps, (out_w, out_h))

    display_enabled = not (NO_DISPLAY or IS_NOTEBOOK or IS_COLAB)

    # ── Startup log ───────────────────────────────────────────────────────────
    print("=" * 58)
    print("  Module A — Traffic Detection V5 Fixed")
    print("=" * 58)
    print(f"  CUDA          : {HAS_CUDA}")
    print(f"  Video FPS     : {fps:.1f}")
    print(f"  SYNC_MODE     : {SYNC_MODE}  "
          f"{'← block/đếm chính xác' if SYNC_MODE else '← async/video mượt'}")
    print(f"  NO_DISPLAY    : {NO_DISPLAY}")
    if not SYNC_MODE:
        print(f"  PLAYBACK_SPEED: {PLAYBACK_SPEED}x")
        print(f"  Frame skip    : {FRAME_SKIP_BY_DENSITY}")
    print(f"  DRY_RUN       : {DRY_RUN}")
    print(f"  ALERT_LOG     : {ALERT_LOG or 'tắt'}")
    print(f"  OUTPUT        : {OUTPUT_VIDEO}")
    if display_enabled:
        print("  Phím          : [p] Pause  [q] Thoát")
    print("=" * 58)

    # ── Async detection thread (SYNC_MODE=false) ──────────────────────────────
    import queue as _queue
    detect_q = _queue.Queue(maxsize=1)
    result_q = _queue.Queue(maxsize=1)
    stop_ev  = threading.Event()

    def _worker():
        while not stop_ev.is_set():
            try:
                # F2 FIX: nhận frame đã resize nhỏ từ queue
                # không copy frame 960px full nữa
                frm = detect_q.get(timeout=1.0)
            except _queue.Empty:
                continue
            trks = tracker.update(detector.detect(frm), frm)
            try:
                result_q.put_nowait(trks)
            except _queue.Full:
                try:
                    result_q.get_nowait()
                    result_q.put_nowait(trks)
                except _queue.Empty:
                    pass

    async_thread = threading.Thread(target=_worker, daemon=True)
    if not SYNC_MODE:
        async_thread.start()

    # ── State ─────────────────────────────────────────────────────────────────
    frame_count     = 0
    traffic_density = "LOW"
    cached_totals   : dict = {}
    last_tracks     : list = []

    spike      = False
    curr_count = 0
    prev_count = 0
    next_skip  = FRAME_SKIP_BY_DENSITY["LOW"] if not SYNC_MODE else 1

    last_agg_wall = time.time()
    last_log_time = time.time()
    perf_start    = time.perf_counter()
    perf_frames   = 0
    smoothed_fps  = 0.0

    wall_anchor  = time.perf_counter()
    video_anchor = camera.get_video_ms()

    density_tally: dict[str, int] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    paused = False

    if display_enabled:
        cv2.namedWindow("Traffic V5", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Traffic V5", 1280, 720)

    try:
        while True:
            if paused:
                key = cv2.waitKey(30) & 0xFF
                if   key == ord("q"): break
                elif key == ord("p"): paused = False
                continue

            ret, raw_frame = camera.read()
            if not ret:
                print("[Module A] Video ended.")
                break

            frame_count  += 1
            t_start       = time.perf_counter()
            video_now_ms  = camera.get_video_ms()
            video_elapsed = (video_now_ms - video_anchor) / 1000.0
            wall_target   = wall_anchor + video_elapsed / PLAYBACK_SPEED
            frame         = processor.process(raw_frame)
            new_tracks    = None

            # ── Detection ─────────────────────────────────────────────────────
            if SYNC_MODE:
                new_tracks   = tracker.update(detector.detect(frame), frame)
                perf_frames += 1

            else:
                if frame_count % next_skip == 0:
                    try:
                        # F2 FIX: đưa frame đã process vào queue — không copy thêm
                        # frame đã là kết quả của processor.process() = đã resize về TARGET_WIDTH
                        # Queue maxsize=1 → nếu full thì worker chưa kịp xử lý → bỏ qua frame này
                        detect_q.put_nowait(frame)
                    except _queue.Full:
                        pass
                    perf_frames += 1
                try:
                    new_tracks = result_q.get_nowait()
                except _queue.Empty:
                    pass

            # ── Update state khi có tracks MỚI ───────────────────────────────
            if new_tracks is not None:
                density_estimator.update(new_tracks)
                traffic_density = density_estimator.get_density()
                curr_count      = density_estimator.get_last_count()

                spike = curr_count > prev_count * 1.5 and curr_count >= 3
                if spike:
                    alert_logger.log(frame_count, video_now_ms / 1000,
                                     traffic_density, curr_count, prev_count, "spike")
                elif traffic_density == "HIGH" and not spike:
                    alert_logger.log(frame_count, video_now_ms / 1000,
                                     traffic_density, curr_count, prev_count, "high_density")

                prev_count = curr_count
                density_tally[traffic_density] = density_tally.get(traffic_density, 0) + 1

                if not SYNC_MODE:
                    next_skip = 1 if spike else FRAME_SKIP_BY_DENSITY.get(traffic_density, 3)

                # F1 FIX: _process_tracks CHỈ gọi khi new_tracks is not None
                # → không bao giờ process last_tracks cũ → không double count
                new_totals = _process_tracks(
                    new_tracks, zone_manager, counter,
                    event_generator, publisher, camera_id, event_counter)
                if new_totals:
                    cached_totals = new_totals

                last_tracks = new_tracks

            # ── Aggregation trigger ────────────────────────────────────────────
            wall_now = time.time()
            if wall_now - last_agg_wall >= AGGREGATION_INTERVAL_SEC:
                last_agg_wall = wall_now
                if not DRY_RUN:
                    threading.Thread(target=_trigger_aggregation,
                                     args=(API_URL, camera_id), daemon=True).start()

            # ── Smoothed FPS (EMA) ─────────────────────────────────────────────
            frame_elapsed = time.perf_counter() - t_start
            inst_fps      = 1.0 / max(frame_elapsed, 1e-6)
            smoothed_fps  = inst_fps if smoothed_fps == 0.0 else smoothed_fps * 0.9 + inst_fps * 0.1

            # ── Draw ──────────────────────────────────────────────────────────
            for t in last_tracks:
                x1, y1, x2, y2 = t["bbox"]
                cx = (x1 + x2) // 2
                cv2.circle(frame, (cx, y2), 4, (255, 60, 60), -1)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (60, 255, 60), 2)
                cv2.putText(frame, f"{t['class_name']} #{t['track_id']}",
                            (x1, max(y1 - 7, 12)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 220, 255), 1, cv2.LINE_AA)

            zone_manager.draw_zone(frame)
            _draw_hud(frame, smoothed_fps, traffic_density,
                      curr_count, spike, next_skip, cached_totals)

            # ── Per-minute log ─────────────────────────────────────────────────
            per_min = counter.get_per_minute(video_now_ms)
            if per_min:
                print(f"[Per-minute] {per_min}")

            # ── Perf log mỗi 5 giây ───────────────────────────────────────────
            if wall_now - last_log_time >= 5:
                last_log_time = wall_now
                zm = zone_manager.stats()
                print(f"[Perf] det={perf_frames:4d} | fps={smoothed_fps:.1f} | "
                      f"video={video_now_ms/1000:.1f}s | density={traffic_density} | "
                      f"zoneIDs={zm['tracked_ids_in_memory']} | "
                      f"q={publisher._queue.qsize() if not DRY_RUN else 0}")

            # ── Output ────────────────────────────────────────────────────────
            out.write(frame)

            if display_enabled:
                if not SYNC_MODE:
                    s = wall_target - time.perf_counter()
                    if s > 0.001:
                        time.sleep(s)
                cv2.imshow("Traffic V5", frame)
                key = cv2.waitKey(1) & 0xFF
                if   key == ord("q"): break
                elif key == ord("p"): paused = True

    except KeyboardInterrupt:
        print("\n[Module A] Interrupted by user")

    finally:
        stop_ev.set()
        if not SYNC_MODE:
            async_thread.join(timeout=3)

        camera.release()
        out.release()
        alert_logger.close()
        cv2.destroyAllWindows()

        elapsed = time.perf_counter() - perf_start
        total   = sum(density_tally.values()) or 1
        events  = event_counter.total if DRY_RUN else "sent async"

        print()
        print("=" * 58)
        print("  SESSION SUMMARY — Module A V5 Fixed")
        print("=" * 58)
        print(f"  Frames detected  : {perf_frames}")
        print(f"  Wall time        : {elapsed:.1f}s")
        print(f"  Avg detect FPS   : {perf_frames / elapsed:.1f}")
        print(f"  Events           : {events}")
        print(f"  Density split    : "
              f"HIGH={density_tally['HIGH']/total:.0%}  "
              f"MED={density_tally['MEDIUM']/total:.0%}  "
              f"LOW={density_tally['LOW']/total:.0%}")
        print(f"  Alerts           : {alert_logger.summary()}")
        print(f"  Zone stats       : {zone_manager.stats()}")
        print(f"  Video saved      : {OUTPUT_VIDEO}")
        print("=" * 58)

    if IS_NOTEBOOK or IS_COLAB:
        print("[Info] Đang load video vào notebook...")
        display_in_notebook(OUTPUT_VIDEO)


if __name__ == "__main__":
    main()