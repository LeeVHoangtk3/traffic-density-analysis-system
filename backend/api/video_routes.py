from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import time
import sys
import os

# FIX IMPORT PATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

router = APIRouter()

def generate_frames():
    from detection.main import latest_frame

    while True:
        if latest_frame is None:
            time.sleep(0.05)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + latest_frame + b"\r\n"
        )

@router.get("/video")
def video_feed():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )