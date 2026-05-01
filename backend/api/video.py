import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

router = APIRouter(tags=["video"])

# Thư mục videos nằm ở gốc project (cùng cấp với backend/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VIDEO_FOLDER = PROJECT_ROOT / "videos"


def _iter_file(file_path: Path, start: int, end: int, chunk_size: int = 1024 * 1024):
    """Generator đọc file theo từng chunk, hỗ trợ Range request."""
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            read_size = min(chunk_size, remaining)
            data = f.read(read_size)
            if not data:
                break
            yield data
            remaining -= len(data)


@router.get("/videos")
def list_videos():
    """Trả về danh sách tất cả video .mp4 có trong thư mục videos/."""
    if not VIDEO_FOLDER.exists():
        return {"videos": []}
    files = [f.name for f in VIDEO_FOLDER.iterdir() if f.suffix.lower() == ".mp4"]
    return {"videos": files}


@router.get("/video/{filename}")
def get_video(filename: str, request: Request):
    """
    Phục vụ video với hỗ trợ HTTP Range requests.
    Trình duyệt cần Range để stream, seek và autoplay video.
    """
    # Ngăn path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ")

    file_path = VIDEO_FOLDER / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Video '{filename}' không tồn tại")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        # Parse Range: bytes=start-end
        try:
            range_value = range_header.strip().replace("bytes=", "")
            if range_value.startswith("-"):
                # Lấy N bytes cuối file (ví dụ: bytes=-1000)
                suffix_length = int(range_value[1:])
                start = max(0, file_size - suffix_length)
                end = file_size - 1
            else:
                parts = range_value.split("-")
                start = int(parts[0])
                if len(parts) > 1 and parts[1]:
                    end = int(parts[1])
                else:
                    end = file_size - 1
        except (ValueError, AttributeError):
            raise HTTPException(status_code=416, detail="Range không hợp lệ")

        if start >= file_size or end >= file_size or start > end:
            raise HTTPException(
                status_code=416,
                detail="Range Not Satisfiable",
                headers={"Content-Range": f"bytes */{file_size}"},
            )

        content_length = end - start + 1
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": "video/mp4",
        }
        return StreamingResponse(
            _iter_file(file_path, start, end),
            status_code=206,
            headers=headers,
            media_type="video/mp4",
        )

    # Không có Range header — trả toàn bộ file
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Type": "video/mp4",
    }
    return StreamingResponse(
        _iter_file(file_path, 0, file_size - 1),
        status_code=200,
        headers=headers,
        media_type="video/mp4",
    )