import os
import sys
import threading
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(BASE_DIR))

import cv2
import json
import requests

from detection.camera_engine import CameraEngine
from detection.engine.frame_processor import FrameProcessor
from detection.engine.detector import Detector
from detection.engine.tracker import Tracker
from detection.engine.counter import VehicleCounter
from detection.engine.density_estimator import DensityEstimator
from detection.engine.zone_manager import ZoneManager
from detection.engine.event_generator import EventGenerator
from detection.integration.publisher import EventPublisher


IS_COLAB = "COLAB_GPU" in os.environ

API_URL      = os.getenv("TRAFFIC_API_URL", "http://127.0.0.1:8000/detection")
VIDEO_SOURCE = os.getenv("TRAFFIC_VIDEO_SOURCE", os.path.join(BASE_DIR, "..", "video_data", "traffic1.mp4"))
MODEL_PATH   = os.getenv("TRAFFIC_MODEL_PATH",   os.path.join(BASE_DIR, "pro_models", "yolov9_img960_ultimate.pt"))

CONF_THRESHOLD = 0.5
SHOW_VIDEO     = True
TARGET_WIDTH   = 960

# Dynamic FRAME_SKIP theo density của frame trước
FRAME_SKIP_BY_DENSITY = {
    "LOW":    5,
    "MEDIUM": 3,
    "HIGH":   1,
}

AGGREGATION_INTERVAL_MS = 15 * 60 * 1000

# ===== Colab / Test flags =====
# DRY_RUN=True: không gửi event đến backend, chỉ detect + track + render
# Dùng khi test trên Colab không có backend local
DRY_RUN        = True
# OUTPUT_VIDEO: đường dẫn file output khi chạy trên Colab
# Set None để tắt ghi file
OUTPUT_VIDEO   = "output_v1.mp4" if IS_COLAB else None


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
    detector          = Detector(MODEL_PATH, conf_threshold=CONF_THRESHOLD)
    tracker           = Tracker(lost_track_buffer=10)
    counter           = VehicleCounter()
    density_estimator = DensityEstimator()
    event_generator   = EventGenerator()
    publisher         = EventPublisher(API_URL)
    zone_manager      = ZoneManager(camera_config["zones"])

    fps = camera.get_fps()
    print(f"Module A Started [V1: Async + Dynamic SKIP]")
    print(f"Video FPS: {fps} | DRY_RUN: {DRY_RUN} | OUTPUT_VIDEO: {OUTPUT_VIDEO}")

    # ===== VideoWriter cho Colab =====
    out = None
    if OUTPUT_VIDEO:
        # Đọc 1 frame để lấy kích thước thực sau khi process
        ret, sample = camera.read()
        if ret:
            sample = processor.process(sample)
            h, w   = sample.shape[:2]
            out    = cv2.VideoWriter(
                OUTPUT_VIDEO,
                cv2.VideoWriter_fourcc(*"mp4v"),
                fps / max(FRAME_SKIP_BY_DENSITY.values()),  # FPS output ước tính
                (w, h),
            )
        # Reset lại video về đầu
        camera.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    frame_count         = 0
    last_aggregation_ms = None
    traffic_density     = "LOW"

    # Perf tracking
    perf_start  = time.time()
    perf_frames = 0

    try:
        while frame_count < 100_000:
            ret, frame = camera.read()
            if not ret:
                print("Video ended.")
                break

            frame_count += 1
            video_ms = camera.get_video_ms()

            # ===== Aggregation trigger theo video time =====
            if last_aggregation_ms is None:
                last_aggregation_ms = video_ms
            elif video_ms - last_aggregation_ms >= AGGREGATION_INTERVAL_MS:
                last_aggregation_ms = video_ms
                if not DRY_RUN:
                    threading.Thread(
                        target=_trigger_aggregation,
                        args=(API_URL, camera_id),
                        daemon=True,
                    ).start()

            # ===== Dynamic FRAME_SKIP =====
            current_skip = FRAME_SKIP_BY_DENSITY.get(traffic_density, 3)
            if frame_count % current_skip != 0:
                continue

            # ===== Pipeline =====
            frame      = processor.process(frame)
            detections = detector.detect(frame)
            tracks     = tracker.update(detections, frame)

            density_estimator.update(tracks)
            traffic_density = density_estimator.get_density()

            perf_frames += 1

            # ===== Process tracks =====
            for track in tracks:
                x1, y1, x2, y2 = track["bbox"]
                track_id        = track["track_id"]
                vehicle_type    = track["class_name"]

                cx        = int((x1 + x2) // 2)
                cy_bottom = int(y2)
                cy_center = int((y1 + y2) // 2)

                cv2.circle(frame, (cx, cy_bottom), 4, (255, 0, 0), -1)
                cv2.circle(frame, (cx, cy_center), 4, (0, 0, 255), -1)

                if zone_manager.check_crossing(track_id, cx, cy_bottom) or \
                   zone_manager.check_crossing(track_id, cx, cy_center):
                    counter.count(vehicle_type)
                    event = event_generator.generate(
                        camera_id=camera_id,
                        track=track,
                        density=traffic_density,
                    )
                    # DRY_RUN: chỉ log event, không gửi HTTP
                    if DRY_RUN:
                        print(f"[DRY_RUN] Event: {event['vehicle_type']} | density: {event['density']}")
                    else:
                        publisher.publish(event)

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{vehicle_type} ID:{track_id}",
                    (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

            zone_manager.draw_zone(frame)
            cv2.putText(frame, f"Density: {traffic_density}",
                (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            y_offset = 80
            for vehicle, cnt in counter.get_totals().items():
                cv2.putText(frame, f"{vehicle}: {cnt}",
                    (30, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                y_offset += 30

            per_min = counter.get_per_minute(video_ms)
            if per_min:
                print(f"[Per-minute] {per_min}")

            # ===== Perf log mỗi 30 frame xử lý =====
            if perf_frames % 30 == 0:   
                elapsed    = time.time() - perf_start
                actual_fps = perf_frames / elapsed
                queue_size = publisher._queue.qsize() if not DRY_RUN else 0
                print(
                    f"[Perf] Frame: {perf_frames:4d} | "
                    f"FPS xử lý: {actual_fps:.1f} | "
                    f"Video time: {video_ms/1000:.1f}s | "
                    f"Density: {traffic_density} | "
                    f"Skip: {current_skip} | "
                    f"Queue: {queue_size}"
                )

            # ===== Ghi video output (Colab) hoặc hiển thị (local) =====
            if out:
                out.write(frame)
            elif not IS_COLAB and SHOW_VIDEO:
                cv2.imshow("Traffic Monitoring - Module A [V1]", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        camera.release()
        if out:
            out.release()
            print(f"Output saved: {OUTPUT_VIDEO}")
        cv2.destroyAllWindows()
        elapsed = time.time() - perf_start
        print(f"Module A Stopped | Tổng frame xử lý: {perf_frames} | Thời gian thực: {elapsed:.1f}s")


if __name__ == "__main__":
    main()