from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter()

VIDEO_FOLDER = "videos"

@router.get("/video/{filename}")
def get_video(filename: str):
    file_path = os.path.join(VIDEO_FOLDER, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video không tồn tại")

    return FileResponse(file_path, media_type="video/mp4")