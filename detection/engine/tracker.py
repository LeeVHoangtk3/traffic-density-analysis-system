from deep_sort_realtime.deepsort_tracker import DeepSort


class Tracker:
    def __init__(self):
        self.tracker = DeepSort(max_age=30)

    def update(self, detections, frame):
        raw_detections = [
            (det["bbox"], det["confidence"], det["class_name"])
            for det in detections
        ]

        tracks = self.tracker.update_tracks(raw_detections, frame=frame)

        results = []

        for track in tracks:
            if not track.is_confirmed():
                continue

            x1, y1, x2, y2 = map(int, track.to_ltrb())

            results.append({
                "track_id": track.track_id,
                "bbox": [x1, y1, x2, y2],
                "class_name": track.det_class
            })

        return results