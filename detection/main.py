import os
import sys

# Define base directory before anything else to ensure correct import paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Add the project root to sys.path so 'detection.*' imports work correctly
sys.path.append(os.path.dirname(BASE_DIR))

# ===== GLOBAL FRAME (for streaming) =====
latest_frame = None

import cv2
import json

from camera_engine import CameraEngine
from engine.frame_processor import FrameProcessor
from engine.detector import Detector
from engine.tracker import Tracker
from engine.counter import VehicleCounter
from engine.density_estimator import DensityEstimator
from engine.zone_manager import ZoneManager
from engine.event_generator import EventGenerator
from integration.publisher import EventPublisher

# ===== Detect if running on Google Colab =====
IS_COLAB = "COLAB_GPU" in os.environ

API_URL = os.getenv("TRAFFIC_API_URL", "http://127.0.0.1:8000/detection")

VIDEO_SOURCE = os.getenv(
    "TRAFFIC_VIDEO_SOURCE",
    os.path.join(BASE_DIR, "..", "traffictrim.mp4")
)

MODEL_PATH = os.getenv(
    "TRAFFIC_MODEL_PATH",
    os.path.join(BASE_DIR, "..", "yolov9c.pt")
)

CONF_THRESHOLD = 0.5

# ===== Performance tuning =====
FRAME_SKIP = 3
SHOW_VIDEO = True
TARGET_WIDTH = 640


def main():
    global latest_frame

    CAMERA_ID = "CAM_01"

    # ===== Load camera config =====
    config_path = os.path.join(
        BASE_DIR,
        "configs_cameras",
        f"{CAMERA_ID.lower()}.json"
    )

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Camera config not found: {config_path}")

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"YOLO model not found: {MODEL_PATH}")

    if isinstance(VIDEO_SOURCE, str) and not VIDEO_SOURCE.isdigit() and not os.path.exists(VIDEO_SOURCE):
        raise FileNotFoundError(
            "Video source not found. Set TRAFFIC_VIDEO_SOURCE or add the file at "
            f"{VIDEO_SOURCE}"
        )

    with open(config_path) as f:
        camera_config = json.load(f)

    zones = camera_config["zones"]

    # ===== Initialize components =====
    camera = CameraEngine(VIDEO_SOURCE)
    processor = FrameProcessor(target_width=TARGET_WIDTH)
    detector = Detector(MODEL_PATH, conf_threshold=CONF_THRESHOLD)
    tracker = Tracker()
    counter = VehicleCounter()
    density_estimator = DensityEstimator()
    event_generator = EventGenerator()
    publisher = EventPublisher(API_URL)
    zone_manager = ZoneManager(zones)

    print("Module A Started")

    frame_count = 0
    MAX_FRAMES = 100000

    # ===== VIDEO WRITER =====
    OUTPUT_FOLDER = os.path.join(BASE_DIR, "..", "videos")
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    output_path = os.path.join(OUTPUT_FOLDER, "output.mp4")

    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = None

    try:
        while frame_count < MAX_FRAMES:

            ret, frame = camera.read()

            if not ret:
                break

            frame_count += 1

            # ===== Skip frame =====
            if frame_count % FRAME_SKIP != 0:
                continue

            # ===== Preprocess =====
            frame = processor.process(frame)

            # ===== INIT VideoWriter khi có frame đầu (SAU KHI RESIZE) =====
            if out is None:
                h, w = frame.shape[:2]
                out = cv2.VideoWriter(output_path, fourcc, 20.0, (w, h))

            # ===== Detection =====
            detections = detector.detect(frame)

            # ===== Tracking =====
            tracks = tracker.update(detections, frame)

            # ===== Density =====
            density_estimator.update(tracks)
            traffic_density = density_estimator.get_density()

            for track in tracks:
                x1, y1, x2, y2 = track["bbox"]
                track_id = track["track_id"]
                vehicle_type = track["class_name"]

                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                cv2.circle(frame, (cx, cy), 4, (255, 0, 0), -1)

                if zone_manager.check_crossing(track_id, cx, cy):
                    counter.count(vehicle_type)

                    event = event_generator.generate(
                        camera_id=CAMERA_ID,
                        track=track,
                        density=traffic_density
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
                    2
                )

            # ===== Draw zones =====
            zone_manager.draw_zone(frame)

            # ===== Draw density =====
            cv2.putText(
                frame,
                f"Density: {traffic_density}",
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2
            )

            # ===== Draw totals =====
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
                    2
                )
                y_offset += 30

            # ===== SAVE VIDEO =====
            if out is not None:
                out.write(frame)

            # ===== STREAM FRAME =====
            if not IS_COLAB and SHOW_VIDEO:
                _, buffer = cv2.imencode('.jpg', frame)
                latest_frame = buffer.tobytes()

    except KeyboardInterrupt:
        print("Interrupted by user")

    finally:
        camera.release()

        if out is not None:
            out.release()

        cv2.destroyAllWindows()

        print("Module A Stopped")


if __name__ == "__main__":
    main()