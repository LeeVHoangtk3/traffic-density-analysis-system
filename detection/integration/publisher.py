import threading
import queue
import requests


class EventPublisher:
    def __init__(self, api_url: str, max_queue: int = 200):
        self.api_url = api_url
        # Queue giới hạn 200 event, tránh memory leak khi backend chậm
        self._queue = queue.Queue(maxsize=max_queue)
        # Daemon thread: tự chết khi main process kết thúc
        # Thay vì gọi requests.post() trực tiếp trong publish() → block 10-50ms
        # Nay giao việc gửi HTTP cho background thread, publish() return ngay
        threading.Thread(target=self._loop, daemon=True).start()

    def publish(self, event: dict) -> None:
        """
        Non-blocking: đẩy vào queue và return ngay lập tức.
        Bản cũ: requests.post() trực tiếp → block vòng lặp chính 10-50ms/event.
        """
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            # Queue đầy → bỏ event cũ nhất, ưu tiên giữ event mới
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(event)
            except queue.Empty:
                pass

    def _loop(self) -> None:
        """Background thread: gửi event tuần tự, không block main loop"""
        while True:
            event = self._queue.get()
            try:
                response = requests.post(self.api_url, json=event, timeout=3)
                response.raise_for_status()
            except Exception as e:
                print("Publish failed:", e)