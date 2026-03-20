import cv2


class FrameProcessor:
    def __init__(self, target_width=1280):
        self.target_width = target_width

    def process(self, frame):
        h, w = frame.shape[:2]
        scale = self.target_width / w
        frame = cv2.resize(frame, (self.target_width, int(h * scale)))
        return frame