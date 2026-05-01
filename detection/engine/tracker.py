import numpy as np
import supervision as sv
from typing import Optional


class Tracker:
    """
    Wrapper ByteTrack với cấu hình tối ưu cho traffic detection VN.

    Thay đổi so với bản gốc:
    - lost_track_buffer: 10 → 90  (giữ ID xe lên đến ~3.6 giây @ 25FPS,
                                   tránh double counting khi xe bị occlusion)
    - track_activation_threshold: 0.25 → 0.35  (giảm track "ma" từ false positive)
    - minimum_matching_threshold: thêm mới = 0.8  (matching chặt hơn khi re-associate)
    """

    def __init__(
        self,
        track_activation_threshold: float = 0.35,
        lost_track_buffer: int = 90,
        minimum_matching_threshold: float = 0.8,
    ):
        self.tracker = sv.ByteTrack(
            track_activation_threshold=track_activation_threshold,
            lost_track_buffer=lost_track_buffer,
            minimum_matching_threshold=minimum_matching_threshold,
        )

    def update(
        self,
        detections: list[dict],
        frame: Optional[np.ndarray] = None,
    ) -> list[dict]:
        """
        Args:
            detections: List of dicts từ Detector, mỗi dict có:
                        {bbox, confidence, class_id, class_name}
            frame:      Reserved cho tương lai (e.g. ReID, visual debug)
        Returns:
            List of dicts: {track_id, bbox, class_name, confidence}
        """
        if not detections:
            return []

        xyxy       = np.array([d["bbox"]       for d in detections], dtype=np.float32)
        confidence = np.array([d["confidence"] for d in detections], dtype=np.float32)
        class_id   = np.array([d["class_id"]   for d in detections], dtype=int)

        id_to_name: dict[int, str] = {
            d["class_id"]: d["class_name"] for d in detections
        }

        sv_detections = sv.Detections(
            xyxy=xyxy,
            confidence=confidence,
            class_id=class_id,
        )

        tracked = self.tracker.update_with_detections(sv_detections)

        if tracked.tracker_id is None:
            return []

        results = []
        for i, tracker_id in enumerate(tracked.tracker_id):
            if tracker_id is None:
                continue

            x1, y1, x2, y2 = tracked.xyxy[i].astype(int)
            cls_id = int(tracked.class_id[i])

            results.append({
                "track_id":   int(tracker_id),
                "bbox":       [x1, y1, x2, y2],
                "class_name": id_to_name.get(cls_id, "unknown"),
                "confidence": float(tracked.confidence[i]),
            })

        return results