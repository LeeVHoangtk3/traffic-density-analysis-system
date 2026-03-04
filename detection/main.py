import os
import cv2

from camera_engine import CameraEngine

from engine.frame_processor import FrameProcessor
from engine.detector import Detector
from engine.tracker import Tracker
from engine.counter import VehicleCounter
from engine.density_estimator import DensityEstimator
from engine.zone_manager import ZoneManager
from engine.event_generator import EventGenerator

from integration.publisher import EventPublisher
# from detection.camera_engine import CameraEngine

# from detection.engine.frame_processor import FrameProcessor
# from detection.engine.detector import Detector
# from detection.engine.tracker import Tracker
# from detection.engine.counter import VehicleCounter
# from detection.engine.density_estimator import DensityEstimator
# from detection.engine.zone_manager import ZoneManager
# from detection.engine.event_generator import EventGenerator

# from detection.integration.publisher import EventPublisher


# ===== Detect if running on Google Colab =====
IS_COLAB = "COLAB_GPU" in os.environ


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

API_URL = "http://localhost:8000/api/events"
VIDEO_SOURCE = os.path.join(BASE_DIR, "..", "traffictrim.mp4")
MODEL_PATH = "yolov9c.pt"

CAMERA_ID = "CAM_01"
LINE_Y = 308
X_START = 100
X_END = 1200
CONF_THRESHOLD = 0.4


def main():

    camera = CameraEngine(VIDEO_SOURCE)
    processor = FrameProcessor(target_width=1280)

    detector = Detector(MODEL_PATH, conf_threshold=CONF_THRESHOLD)
    tracker = Tracker()
    counter = VehicleCounter()
    density_estimator = DensityEstimator()

    event_generator = EventGenerator()
    publisher = EventPublisher(API_URL)

    zone_manager = ZoneManager(
        line_y=LINE_Y,
        x_start=X_START,
        x_end=X_END
    )

    print("🚀 Module A Started")

    frame_count = 0
    MAX_FRAMES = 100000   # tránh loop vô hạn trên Colab

    try:

        while frame_count < MAX_FRAMES:

            ret, frame = camera.read()
            if not ret:
                break

            frame_count += 1

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

                cv2.circle(frame, (cx, cy), 3, (255,0,0), -1)

                # ===== Line crossing =====
                if zone_manager.check_crossing(track_id, cx, cy):

                    counter.count(vehicle_type)

                    event = event_generator.generate(
                        camera_id=CAMERA_ID,
                        track=track,
                        density=traffic_density
                    )

                    publisher.publish(event)
                    # print(f"📤 Published event: {event}") #for test

                # ===== Draw bounding box =====
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

            # ===== Draw counting zone =====
            zone_manager.draw_zone(frame)

            # # highlight zone area
            cv2.rectangle(
                frame,
                (zone_manager.x_start, zone_manager.line_y - 5),
                (zone_manager.x_end, zone_manager.line_y + 5),
                (0,0,255),
                1
            )

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

            # ===== Show video (only local) =====
            if not IS_COLAB:

                cv2.imshow("Traffic Monitoring - Module A", frame)

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