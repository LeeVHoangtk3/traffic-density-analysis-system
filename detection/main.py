import os
import sys
import threading
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(BASE_DIR))
sys.path.append(BASE_DIR)

import cv2
import json
import torch
import requests

from camera_engine import CameraEngine
from engine.frame_processor import FrameProcessor
from engine.detector import Detector
from engine.tracker import Tracker
from engine.counter import VehicleCounter
from engine.density_estimator import DensityEstimator
from engine.zone_manager import ZoneManager
from engine.event_generator import EventGenerator
from integration.publisher import EventPublisher


IS_COLAB = "COLAB_GPU" in os.environ

API_URL      = os.getenv("TRAFFIC_API_URL",       "http://127.0.0.1:8000/detection")
VIDEO_SOURCE = os.getenv("TRAFFIC_VIDEO_SOURCE",   os.path.join(BASE_DIR, "..", "video_data", "traffic1.mp4"))
MODEL_PATH   = os.getenv("TRAFFIC_MODEL_PATH",     os.path.join(BASE_DIR, "pro_models", "yolov9_img960_ultimate.pt"))
OUTPUT_VIDEO = os.getenv("TRAFFIC_OUTPUT_VIDEO",   "output_v2.mp4" if IS_COLAB else None)

CONF_THRESHOLD = 0.40
SHOW_VIDEO     = True
TARGET_WIDTH   = 960  # cố định 960 vì model train với imgsz=960

HAS_CUDA = torch.cuda.is_available()
FRAME_SKIP_BY_DENSITY = {
    "LOW":    5  if HAS_CUDA else 10,
    "MEDIUM": 3  if HAS_CUDA else 6,
    "HIGH":   1  if HAS_CUDA else 2,
}

AGGREGATION_INTERVAL_SEC = 15 * 60

DRY_RUN = False


def _trigger_aggregation(api_url: str, camera_id: str) -> None:
    try:
        base_url = api_url.rsplit("/", 1)[0] if "/" in api_url else api_url
        resp = requests.post(
            f"{base_url}/aggregation/compute",
            params={"camera_id": camera_id},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"[Aggregation] {data['vehicle_count']} xe | {data['congestion_level']}")
        else:
            print(f"[Aggregation] HTTP {resp.status_code}")
    except Exception as exc:
        print(f"[Aggregation] Lỗi: {exc}")


def _get_output_size(video_source, target_width: int) -> tuple[int, int]:
    src    = int(video_source) if str(video_source).isdigit() else video_source
    cap    = cv2.VideoCapture(src)
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if orig_w == 0 or orig_h == 0:
        return target_width, target_width
    scale = target_width / orig_w
    return target_width, int(orig_h * scale)


def main():
    camera_id   = "CAM_01"
    config_path = os.path.join(BASE_DIR, "configs_cameras", f"{camera_id.lower()}.json")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Camera config not found: {config_path}")
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"YOLO model not found: {MODEL_PATH}")
    if isinstance(VIDEO_SOURCE, str) and not VIDEO_SOURCE.isdigit() and not os.path.exists(VIDEO_SOURCE):
        raise FileNotFoundError(f"Video source not found: {VIDEO_SOURCE}")

    with open(config_path, encoding="utf-8") as f:
        camera_config = json.load(f)

    # ===== Initialize components =====
    camera            = CameraEngine(VIDEO_SOURCE)
    processor         = FrameProcessor(target_width=TARGET_WIDTH)
    detector          = Detector(MODEL_PATH, conf_threshold=CONF_THRESHOLD, img_size=TARGET_WIDTH)
    tracker           = Tracker()
    counter           = VehicleCounter()
    density_estimator = DensityEstimator(window=30)
    event_generator   = EventGenerator()
    publisher         = EventPublisher(API_URL)
    zone_manager      = ZoneManager(camera_config["zones"])

    fps = camera.get_fps()
    print(f"[Module A] Started V2")
    print(f"  Video FPS   : {fps}")
    print(f"  TARGET_WIDTH: {TARGET_WIDTH}")
    print(f"  CUDA        : {HAS_CUDA}")
    print(f"  DRY_RUN     : {DRY_RUN}")
    print(f"  OUTPUT_VIDEO: {OUTPUT_VIDEO}")
    print(f"  Frame skip  : {FRAME_SKIP_BY_DENSITY}")

    # ===== VideoWriter (Colab only) =====
    out = None
    if OUTPUT_VIDEO:
        out_w, out_h = _get_output_size(VIDEO_SOURCE, TARGET_WIDTH)
        out = cv2.VideoWriter(
            OUTPUT_VIDEO,
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,  # giữ FPS gốc để video không bị tua nhanh/chậm
            (out_w, out_h),
        )

    # ===== State =====
    frame_count         = 0
    traffic_density     = "LOW"
    cached_totals       = {}
    dry_run_event_count = 0
    last_tracks         = []

    # FIX #3: khởi tạo spike và curr_last_count trước vòng lặp
    # tránh NameError khi frame đầu tiên bị skip
    spike           = False
    curr_last_count = 0
    prev_last_count = 0
    next_skip       = FRAME_SKIP_BY_DENSITY["LOW"]

    last_aggregation_wall = time.time()
    perf_start    = time.time()
    perf_frames   = 0
    last_log_time = time.time()

    try:
        while True:
            ret, raw_frame = camera.read()
            if not ret:
                print("[Module A] Video ended.")
                break

            frame_count += 1
            frame = processor.process(raw_frame)

            is_detection_frame = (frame_count % next_skip == 0)

            if is_detection_frame:
                # ===== Aggregation trigger (wall clock) =====
                wall_now = time.time()
                if wall_now - last_aggregation_wall >= AGGREGATION_INTERVAL_SEC:
                    last_aggregation_wall = wall_now
                    if not DRY_RUN:
                        threading.Thread(
                            target=_trigger_aggregation,
                            args=(API_URL, camera_id),
                            daemon=True,
                        ).start()

                # ===== Detection pipeline =====
                detections = detector.detect(frame)
                tracks     = tracker.update(detections, frame)

                density_estimator.update(tracks)
                traffic_density = density_estimator.get_density()

                curr_last_count = density_estimator.get_last_count()
                spike           = curr_last_count > prev_last_count * 1.5 and curr_last_count >= 3
                prev_last_count = curr_last_count
                next_skip       = 1 if spike else FRAME_SKIP_BY_DENSITY.get(traffic_density, 3)

                perf_frames += 1
                last_tracks = tracks

                for track in tracks:
                    x1, y1, x2, y2 = track["bbox"]
                    track_id     = track["track_id"]
                    vehicle_type = track["class_name"]

                    cx        = (x1 + x2) // 2
                    cy_bottom = y2  # FIX #4: dùng cy_bottom (điểm tiếp đất), không phải center

                    # FIX #2: dùng tên biến zone_dir thay vì direction
                    # tránh ghi đè biến direction cấp camera
                    zone_dir = zone_manager.check_crossing(track_id, cx, cy_bottom)
                    if zone_dir:
                        counter.count(vehicle_type)
                        cached_totals = counter.get_totals()

                        # FIX #1: bỏ density khỏi generate() — event_generator không nhận nữa
                        event = event_generator.generate(
                            camera_id=camera_id,
                            track=track,
                            direction=zone_dir,
                        )
                        if DRY_RUN:
                            dry_run_event_count += 1
                        else:
                            publisher.publish(event)

            else:
                # Frame bị skip: dùng lại tracks của frame trước để vẽ mượt
                tracks = last_tracks

            # ===== DRAWING — vẽ lên mọi frame để video output mượt =====
            for track in tracks:
                x1, y1, x2, y2 = track["bbox"]
                track_id     = track["track_id"]
                vehicle_type = track["class_name"]

                cx        = (x1 + x2) // 2
                cy_bottom = y2

                cv2.circle(frame, (cx, cy_bottom), 4, (255, 0, 0), -1)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    f"{vehicle_type} ID:{track_id}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2,
                )

            zone_manager.draw_zone(frame)

            # ===== HUD =====
            hud = (
                f"Density:{traffic_density} | "
                f"Skip:{next_skip} | "
                f"Spike:{'YES' if spike else 'no'} | "
                f"Tracks:{curr_last_count}"
            )
            cv2.putText(frame, hud, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

            y_offset = 85
            for vehicle, cnt in cached_totals.items():
                cv2.putText(
                    frame,
                    f"{vehicle}: {cnt}",
                    (30, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2,
                )
                y_offset += 30

            video_ms = camera.get_video_ms()
            per_min  = counter.get_per_minute(video_ms)
            if per_min:
                print(f"[Per-minute] {per_min}")

            # ===== Perf log mỗi 5 giây =====
            if time.time() - last_log_time >= 5:
                last_log_time = time.time()
                elapsed    = time.time() - perf_start
                actual_fps = perf_frames / elapsed if elapsed > 0 else 0
                queue_size = publisher._queue.qsize() if not DRY_RUN else 0
                zm_stats   = zone_manager.stats()
                print(
                    f"[Perf] Frames:{perf_frames:4d} | "
                    f"FPS:{actual_fps:.1f} | "
                    f"Density:{traffic_density} | "
                    f"Skip:{next_skip} | "
                    f"ZoneIDs:{zm_stats['tracked_ids_in_memory']} | "
                    f"Cooldown-blocked:{zm_stats['cooldown_blocked']} | "
                    f"Queue:{queue_size}"
                )

            # ===== Output =====
            if out:
                out.write(frame)
            elif not IS_COLAB and SHOW_VIDEO:
                cv2.imshow("Traffic Monitoring V2", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:
        print("[Module A] Interrupted by user")
    finally:
        camera.release()
        if out:
            out.release()
            print(f"[Module A] Output saved: {OUTPUT_VIDEO}")
        cv2.destroyAllWindows()
        elapsed = time.time() - perf_start
        print(
            f"\n[Module A] Stopped"
            f"\n  Frames processed : {perf_frames}"
            f"\n  Wall time        : {elapsed:.1f}s"
            f"\n  Avg FPS          : {perf_frames / elapsed:.1f}"
            f"\n  Events generated : {dry_run_event_count}"
            f"\n  Zone stats       : {zone_manager.stats()}"
        )


if __name__ == "__main__":
    main()