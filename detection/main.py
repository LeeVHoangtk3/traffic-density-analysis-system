import os
import sys
import threading
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(BASE_DIR))
# ===== ADD THIS =====
latest_frame = None
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
        raise FileNotFoundError(f"Video source not found: {VIDEO_SOURCE}")

    with open(config_path, encoding="utf-8") as f:
        camera_config = json.load(f)

    # ===== Fix missing variables =====
    zones = camera_config.get("zones", [])
    direction = camera_config.get("direction", "inbound")
    camera_id = CAMERA_ID
    DRY_RUN = False
    FRAME_SKIP_BY_DENSITY = {"low": 3, "medium": 2, "high": 1, "severe": 1}
    prev_last_count = 0
    perf_frames = 0
    perf_start = time.time()
    dry_run_event_count = 0

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

    out_video = None
    output_video_path = os.path.join(BASE_DIR, "..", "videos", "output.mp4")
    os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    try:

        while frame_count < MAX_FRAMES:

            ret, frame = camera.read()
            if not ret:
                print("[Module A] Video ended.")
                break

            frame_count += 1
            # ===== Skip frame để tăng tốc =====
            if frame_count % FRAME_SKIP != 0:
                continue

            # ===== Frame preprocessing =====
            frame = processor.process(frame)

            if out_video is None:
                h, w = frame.shape[:2]
                out_video = cv2.VideoWriter(output_video_path, fourcc, 30.0 / FRAME_SKIP, (w, h))

            # ===== Detection =====
            detections = detector.detect(frame)
            tracks     = tracker.update(detections, frame)

            # ===== Density estimation =====
            density_estimator.update(tracks)
            traffic_density = density_estimator.get_density()

            # ===== Spike detection → next frame skip =====
            curr_last_count = density_estimator.get_last_count()
            spike           = curr_last_count > prev_last_count * 1.5 and curr_last_count >= 3
            prev_last_count = curr_last_count
            next_skip       = 1 if spike else FRAME_SKIP_BY_DENSITY.get(traffic_density, 3)

            perf_frames += 1

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
                    cached_totals = counter.get_totals()

                    event = event_generator.generate(
                        camera_id=camera_id,
                        track=track,
                        direction=direction,
                        density=traffic_density,
                    )
                    if DRY_RUN:
                        dry_run_event_count += 1
                    else:
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
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2,
                )

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
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2,
                )
                y_offset += 30

            # ===== Draw traffic light status =====
            light_status_path = os.path.join(BASE_DIR, "..", "light_status.json")
            if os.path.exists(light_status_path):
                try:
                    with open(light_status_path, "r") as f:
                        light_data = json.load(f)
                    green_time = light_data.get("green_time", 0)
                    phase = light_data.get("phase", "")
                    
                    # Draw text background
                    text = f"LIGHT: {phase} - {green_time}s"
                    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
                    cv2.rectangle(frame, (30, 110 - th - 5), (30 + tw + 10, 110 + 5), (0, 0, 0), -1)
                    
                    cv2.putText(
                        frame,
                        text,
                        (35, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2
                    )
                except Exception:
                    pass

            # ===== Show video (local only) =====
            if not IS_COLAB and SHOW_VIDEO:
                # ===== ADD THIS =====
                global latest_frame

                _, buffer = cv2.imencode('.jpg', frame)
                latest_frame = buffer.tobytes()
                
            if out_video is not None:
                out_video.write(frame)

    except KeyboardInterrupt:

        print("Interrupted by user")

    finally:
        if out_video is not None:
            out_video.release()
        camera.release()

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