import cv2
import numpy as np


class ZoneManager:

    def __init__(self, zones):
        self.zones = zones
        self.counted_ids = set()

    def check_crossing(self, track_id, cx, cy):

        point = (cx, cy)

        for zone in self.zones:

            polygon = np.array(zone["points"], np.int32)

            inside = cv2.pointPolygonTest(polygon, point, False)

            if inside >= 0:

                if track_id not in self.counted_ids:

                    self.counted_ids.add(track_id)
                    return True

        return False


    def draw_zone(self, frame):

        for zone in self.zones:

            pts = np.array(zone["points"], np.int32)

            cv2.polylines(
                frame,
                [pts],
                True,
                (255,0,255),
                3
            )