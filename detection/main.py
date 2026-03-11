import os
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


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

API_URL = "http://127.0.0.1:8000/detection"
VIDEO_SOURCE = os.path.join(BASE_DIR, "..", "traffictrim.mp4")
MODEL_PATH = "yolov9c.pt"

CONF_THRESHOLD = 0.5
# ===== Performance tuning =====
FRAME_SKIP = 3        # skip frames để tăng tốc
SHOW_VIDEO = False    # tắt nếu muốn chạy cực nhanh
TARGET_WIDTH = 640    # resize nhỏ hơn để YOLO chạy nhanh

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

    print("🚀 Module A Started")

    frame_count = 0
    MAX_FRAMES = 100000

    try:

        while frame_count < MAX_FRAMES:

            ret, frame = camera.read()

            if not ret:
                break

            frame_count += 1
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

        print("🛑 Interrupted by user")

    finally:

        camera.release()

        cv2.destroyAllWindows()

        print("🛑 Module A Stopped")


if __name__ == "__main__":
    main()