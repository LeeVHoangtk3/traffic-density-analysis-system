import os
import sys
import time
import threading
import requests

# Define base directory before anything else to ensure correct import paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Add the project root to sys.path so 'detection.*' imports work correctly
sys.path.append(os.path.dirname(BASE_DIR))

import cv2
import json

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

API_URL = os.getenv("TRAFFIC_API_URL", "http://127.0.0.1:8000/detection")
VIDEO_SOURCE = os.getenv(
    "TRAFFIC_VIDEO_SOURCE",
    os.path.join(BASE_DIR, "..", "traffictrim.mp4"),
)

MODEL_PATH = os.getenv(
    "TRAFFIC_MODEL_PATH",
    os.path.join(BASE_DIR, "pro_models", "yolov9_img960_ultimate.pt")
)

CONF_THRESHOLD = 0.5
# ===== Performance tuning =====
FRAME_SKIP = 3        # skip frames để tăng tốc
SHOW_VIDEO = True    # tắt nếu muốn chạy cực nhanh
TARGET_WIDTH = 960    # resize nhỏ hơn để YOLO chạy nhanh

def main():
    camera_id = "CAM_01"
    config_path = os.path.join(
        BASE_DIR,
        "configs_cameras",
        f"{camera_id.lower()}.json",
    )

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Camera config not found: {config_path}")

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"YOLO model not found: {MODEL_PATH}")

    if (
        isinstance(VIDEO_SOURCE, str)
        and not VIDEO_SOURCE.isdigit()
        and not os.path.exists(VIDEO_SOURCE)
    ):
        raise FileNotFoundError(
            "Video source not found. Set TRAFFIC_VIDEO_SOURCE or add the file at "
            f"{VIDEO_SOURCE}"
        )

    with open(config_path, encoding="utf-8") as file:
        camera_config = json.load(file)

    zones = camera_config["zones"]

    camera = CameraEngine(VIDEO_SOURCE)
    processor = FrameProcessor(target_width=TARGET_WIDTH)

    detector = Detector(
        MODEL_PATH,
        conf_threshold=CONF_THRESHOLD
    )

    tracker = Tracker(lost_track_buffer=10)

    counter = VehicleCounter()
    density_estimator = DensityEstimator()
    event_generator = EventGenerator()
    publisher = EventPublisher(API_URL)
    zone_manager = ZoneManager(zones)

    print("Module A Started")

    frame_count = 0
    max_frames = 100000
    last_aggregation_time = time.time()

    try:
        while frame_count < max_frames:
            ret, frame = camera.read()
            if not ret:
                break

            frame_count += 1

            now = time.time()
            if now - last_aggregation_time >= AGGREGATION_INTERVAL:
                last_aggregation_time = now
                threading.Thread(
                    target=_trigger_aggregation,
                    args=(API_URL, camera_id),
                    daemon=True,
                ).start()

            if frame_count % FRAME_SKIP != 0:
                continue

            frame = processor.process(frame)
            detections = detector.detect(frame)
            tracks = tracker.update(detections, frame)

            density_estimator.update(tracks)
            traffic_density = density_estimator.get_density()

            for track in tracks:
                x1, y1, x2, y2 = track["bbox"]
                track_id = track["track_id"]
                vehicle_type = track["class_name"]

                cx = int((x1 + x2) // 2)
                cy_bottom = int(y2)
                cy_center = int((y1 + y2) // 2)

                # draw center points
                cv2.circle(frame, (cx, cy_bottom), 4, (255, 0, 0), -1)
                cv2.circle(frame, (cx, cy_center), 4, (0, 0, 255), -1)

                # ===== Check zone crossing =====
                if zone_manager.check_crossing(track_id, cx, cy_bottom) or \
                zone_manager.check_crossing(track_id, cx, cy_center):

                    counter.count(vehicle_type)
                    event = event_generator.generate(
                        camera_id=camera_id,
                        track=track,
                        density=traffic_density,
                    )
                    publisher.publish(event)

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    f"{vehicle_type} ID:{track_id}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 255),
                    2,
                )

            zone_manager.draw_zone(frame)

            cv2.putText(
                frame,
                f"Density: {traffic_density}",
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2,
            )

            totals = counter.get_totals()
            y_offset = 80
            for vehicle, count in totals.items():
                cv2.putText(
                    frame,
                    f"{vehicle}: {count}",
                    (30, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )
                y_offset += 30

            if not IS_COLAB and SHOW_VIDEO:
                cv2.imshow("Traffic Monitoring - Module A", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        camera.release()
        cv2.destroyAllWindows()
        print("Module A Stopped")


if __name__ == "__main__":
    main()
