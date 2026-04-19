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


# ===== Detect if running on Google Colab =====
IS_COLAB = "COLAB_GPU" in os.environ


API_URL = os.getenv("TRAFFIC_API_URL", "http://127.0.0.1:8000/detection")
VIDEO_SOURCE = os.getenv(
    "TRAFFIC_VIDEO_SOURCE",
    os.path.join(BASE_DIR, "..", "traffictrim.mp4")
)

# ĐÂY LÀ NƠI BẠN CHỌN MODEL YOLOv9 CỦA MÌNH

# MODEL_PATH = os.path.join(BASE_DIR, "pro_models", "yolov9c.pt")
MODEL_PATH = os.getenv(
    "TRAFFIC_MODEL_PATH",
    os.path.join(BASE_DIR, "..", "yolov9c.pt")
)

CONF_THRESHOLD = 0.5
# ===== Performance tuning =====
FRAME_SKIP = 3        # skip frames để tăng tốc
SHOW_VIDEO = True   # tắt nếu muốn chạy cực nhanh
TARGET_WIDTH = 640    # resize nhỏ hơn để YOLO chạy nhanh

# ===== Aggregation trigger =====
AGGREGATION_INTERVAL = 15 * 60  # 15 phút tính bằng giây


def _trigger_aggregation(api_url: str, camera_id: str):
    """
    Gọi POST /aggregation/compute để backend gom dữ liệu 15 phút vừa qua.
    Chạy trong thread riêng để không block vòng lặp detect.
    """
    try:
        url = f"{api_url.rstrip('/aggregation').rstrip('/detection')}"
        # Xây lại base URL từ API_URL (bỏ path /detection)
        base_url = api_url.rsplit("/", 1)[0] if "/" in api_url else api_url
        endpoint = f"{base_url}/aggregation/compute"
        resp = requests.post(endpoint, params={"camera_id": camera_id}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print(
                f"[Aggregation] Window ghi nhận: "
                f"{data['vehicle_count']} xe | "
                f"Mức độ: {data['congestion_level']}"
            )
        else:
            print(f"[Aggregation] HTTP {resp.status_code}: {resp.text}")
    except Exception as exc:
        print(f"[Aggregation] Lỗi khi gọi API tổng hợp: {exc}")


def main():

    # ===== Camera ID =====
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

    detector = Detector(
        MODEL_PATH,
        conf_threshold=CONF_THRESHOLD
    )

    tracker = Tracker()

    counter = VehicleCounter()

    density_estimator = DensityEstimator()

    event_generator = EventGenerator()

    publisher = EventPublisher(API_URL)

    zone_manager = ZoneManager(zones)

    print("Module A Started")

    frame_count = 0
    MAX_FRAMES = 100000
    # Thời điểm gọi aggregation lần cuối (tính bằng time.time())
    last_aggregation_time = time.time()

    try:

        while frame_count < MAX_FRAMES:

            ret, frame = camera.read()

            if not ret:
                break

            frame_count += 1

            # ===== Trigger aggregation mỗi 15 phút =====
            now = time.time()
            if now - last_aggregation_time >= AGGREGATION_INTERVAL:
                last_aggregation_time = now
                threading.Thread(
                    target=_trigger_aggregation,
                    args=(API_URL, CAMERA_ID),
                    daemon=True,
                ).start()

            # ===== Skip frame để tăng tốc =====
            if frame_count % FRAME_SKIP != 0:
                continue

            # ===== Frame preprocessing =====
            frame = processor.process(frame)

            # ===== Detection =====
            detections = detector.detect(frame)

            # ===== Tracking =====
            tracks = tracker.update(detections, frame)

            # ===== Density estimation =====
            density_estimator.update(tracks)

            traffic_density = density_estimator.get_density()

            # ===== Process tracks =====
            for track in tracks:

                x1, y1, x2, y2 = track["bbox"]

                track_id = track["track_id"]

                vehicle_type = track["class_name"]

                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                # draw center point
                cv2.circle(frame,(cx,cy),4,(255,0,0),-1)

                # ===== Check zone crossing =====
                if zone_manager.check_crossing(track_id, cx, cy):

                    counter.count(vehicle_type)

                    event = event_generator.generate(
                        camera_id=CAMERA_ID,
                        track=track,
                        density=traffic_density
                    )

                    publisher.publish(event)

                    # print("EVENT:", event)

                # ===== Draw bounding box =====
                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

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

            # ===== Draw vehicle totals =====
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

            # ===== Show video (local only) =====
            if not IS_COLAB and SHOW_VIDEO:

                cv2.imshow(
                    "Traffic Monitoring - Module A",
                    frame
                )

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
