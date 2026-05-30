from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["video"])


# ================== PROJECT ROOT ==================
# traffic-density-analysis-system/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ================== VIDEO FOLDER ==================
# traffic-density-analysis-system/data/video/
VIDEO_FOLDER = PROJECT_ROOT / "data" / "video"

# ================== DEFAULT VIDEO ==================
DEFAULT_VIDEO = "cam01-traffic3.mp4"


def _iter_file(
    file_path: Path,
    start: int,
    end: int,
    chunk_size: int = 1024 * 1024
):
    """
    Stream file theo chunk
    (hỗ trợ video range streaming)
    """

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


@router.get("/video")
def get_video(
    request: Request,
    camera_id: str | None = None,
    video_name: str | None = None
):
    selected_video = DEFAULT_VIDEO
    if video_name:
        selected_video = video_name
    elif camera_id:
        if camera_id.lower() == "cam01":
            selected_video = "cam01-traffic3.mp4"
        elif camera_id.lower() == "cam02":
            selected_video = "cam02-traffic8.mp4"
        elif camera_id.lower() == "cam03":
            selected_video = "cam03-traffic1.mp4"
        else:
            selected_video = f"{camera_id.lower()}-traffic3.mp4"

    # ================= SMART VIDEO SELECTION =================
    # Tự động phát hiện và ưu tiên phát tệp video kết quả đã qua xử lý AI (_output.mp4)
    file_path = VIDEO_FOLDER / selected_video
    
    if selected_video.endswith(".mp4") and not selected_video.endswith("_output.mp4"):
        output_name = selected_video.replace(".mp4", "_output.mp4")
        output_path_local = VIDEO_FOLDER / output_name
        output_path_root = PROJECT_ROOT / output_name
        output_path_test_data = PROJECT_ROOT / "test_data" / "output" / output_name
        
        if output_path_local.exists() and output_path_local.is_file():
            file_path = output_path_local
            print(f"[Smart-Stream] Phát hiện video đã xử lý AI (VIDEO_FOLDER): {output_name}")
        elif output_path_test_data.exists() and output_path_test_data.is_file():
            file_path = output_path_test_data
            print(f"[Smart-Stream] Phát hiện video đã xử lý AI (test_data/output): {output_name}")
        elif output_path_root.exists() and output_path_root.is_file():
            file_path = output_path_root
            print(f"[Smart-Stream] Phát hiện video đã xử lý AI (PROJECT_ROOT): {output_name}")

    # Fallback kiểm tra nếu file_path không tồn tại ở data/video
    if not (file_path.exists() and file_path.is_file()):
        project_root_raw = PROJECT_ROOT / selected_video
        if project_root_raw.exists() and project_root_raw.is_file():
            file_path = project_root_raw
        else:
            # Fallback cứng về video mặc định để tránh lỗi 404
            file_path = VIDEO_FOLDER / DEFAULT_VIDEO

    # ================= DEBUG =================
    print("PROJECT_ROOT:", PROJECT_ROOT)
    print("VIDEO_FOLDER:", VIDEO_FOLDER)
    print("FILE_PATH PREFERRED:", file_path)
    print("EXISTS:", file_path.exists())
    print("CWD:", Path.cwd())
    # =========================================

    # ================= CHECK FILE =================
    if not file_path.exists() or not file_path.is_file():

        raise HTTPException(
            status_code=404,
            detail=f"Video '{selected_video}' không tồn tại tại {file_path}"
        )

    file_size = file_path.stat().st_size

    range_header = request.headers.get("range")

    # ================= RANGE REQUEST =================
    if range_header:

        try:

            range_value = range_header.strip().replace(
                "bytes=",
                ""
            )

            # bytes=-500
            if range_value.startswith("-"):

                suffix_length = int(range_value[1:])

                start = max(
                    0,
                    file_size - suffix_length
                )

                end = file_size - 1

            else:

                parts = range_value.split("-")

                start = int(parts[0])

                if len(parts) > 1 and parts[1]:

                    end = int(parts[1])

                else:
                    end = file_size - 1

        except (ValueError, AttributeError):

            raise HTTPException(
                status_code=416,
                detail="Range không hợp lệ"
            )

        # ================= INVALID RANGE =================
        if (
            start >= file_size
            or end >= file_size
            or start > end
        ):

            raise HTTPException(
                status_code=416,
                detail="Range Not Satisfiable",
                headers={
                    "Content-Range": f"bytes */{file_size}"
                },
            )

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Type": "video/mp4",
        }

        return StreamingResponse(
            _iter_file(
                file_path,
                start,
                end
            ),
            status_code=206,
            headers=headers,
            media_type="video/mp4",
        )

    # ================= FULL VIDEO =================
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Type": "video/mp4",
    }

    return StreamingResponse(
        _iter_file(
            file_path,
            0,
            file_size - 1
        ),
        status_code=200,
        headers=headers,
        media_type="video/mp4",
    )