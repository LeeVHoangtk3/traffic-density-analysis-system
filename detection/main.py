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


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_URL = "http://localhost:8000/api/events"
VIDEO_SOURCE = os.path.join(BASE_DIR, "..", "traffictrim.mp4")
MODEL_PATH = "yolov9c.pt"

CAMERA_ID = "CAM_01"
LINE_Y = 308
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
        line_y=308,
        x_start=300,
        x_end=1000
    )

    print("🚀 Module A Started")

    while True:
        ret, frame = camera.read()
        if not ret:
            break

        frame = processor.process(frame)

        detections = detector.detect(frame)
        tracks = tracker.update(detections, frame)

        density_estimator.update(tracks)
        traffic_density = density_estimator.get_density()

        for track in tracks:
            x1, y1, x2, y2 = track["bbox"]
            track_id = track["track_id"]
            vehicle_type = track["class_name"]

            cy = (y1 + y2) // 2
            cx = (x1 + x2) // 2

            if zone_manager.check_crossing(track_id, cx, cy):
                counter.count(vehicle_type)

                event = event_generator.generate(
                    camera_id=CAMERA_ID,
                    track=track,
                    density=traffic_density
                )

                # print("📦 EVENT:", event) #for test
                publisher.publish(event)

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame,
                        f"{vehicle_type} ID:{track_id}",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 255),
                        2)

        zone_manager.draw_zone(frame)

        cv2.putText(frame,
                    f"Density: {traffic_density}",
                    (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2)

        totals = counter.get_totals()
        y_offset = 80
        for vehicle, count in totals.items():
            cv2.putText(frame,
                        f"{vehicle}: {count}",
                        (30, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 255),
                        2)
            y_offset += 30

        cv2.imshow("Traffic Monitoring - Module A", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()
    print("🛑 Module A Stopped")


if __name__ == "__main__":
    main()