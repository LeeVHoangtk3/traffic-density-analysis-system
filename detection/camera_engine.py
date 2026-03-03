import cv2


class CameraEngine:
    def __init__(self, source):
        self.cap = cv2.VideoCapture(source)
        print("Video opened:", self.cap.isOpened())

    def read(self):
        return self.cap.read()

    def release(self):
        self.cap.release()