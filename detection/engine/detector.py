from ultralytics import YOLO

# COCO vehicle classes
VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}


# Custom model classes
# VEHICLE_CLASSES = {
#     0: "bus",
#     1: "car",
#     2: "motorcycle",
#     3: "truck"
# }

class Detector:
    def __init__(self, model_path, conf_threshold=0.4):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold

    def detect(self, frame):
        results = self.model(frame, verbose=False)[0]
        detections = []

        for box in results.boxes:
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])

            if conf < self.conf_threshold:
                continue

            if cls_id not in VEHICLE_CLASSES:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            detections.append({
                "bbox": [x1, y1, x2, y2],
                "confidence": conf,
                "class_id": cls_id,
                "class_name": VEHICLE_CLASSES[cls_id]
            })

        return detections