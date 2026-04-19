import requests


class EventPublisher:
    def __init__(self, api_url):
        self.api_url = api_url

    def publish(self, event):
        try:
            response = requests.post(self.api_url, json=event, timeout=3)
            response.raise_for_status()
        except Exception as e:
            print("Publish failed:", e)
