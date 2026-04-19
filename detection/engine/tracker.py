from deep_sort_realtime.deepsort_tracker import DeepSort


class Tracker:
    def __init__(self):
        self.tracker = DeepSort(max_age=30)

    def update(self, detections, frame):
        raw_detections = []

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]

            w = x2 - x1
            h = y2 - y1

            raw_detections.append(
                ([x1, y1, w, h], det["confidence"], det["class_name"])
            )

        tracks = self.tracker.update_tracks(raw_detections, frame=frame)

        results = []

        for track in tracks:
            if not track.is_confirmed():
                continue

            x1, y1, x2, y2 = map(int, track.to_ltrb())
            confidence = getattr(track, "det_conf", None)

            results.append({
                "track_id": track.track_id,
                "bbox": [x1, y1, x2, y2],
                "class_name": track.det_class,
                "confidence": float(confidence) if confidence is not None else None,
            })

        return results
