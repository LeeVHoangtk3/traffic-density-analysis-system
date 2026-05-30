from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["video"])


# ================== PROJECT ROOT ==================
# traffic-density-analysis-system/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ================== VIDEO FOLDERS ==================
# traffic-density-analysis-system/data/video/
VIDEO_FOLDER = PROJECT_ROOT / "data" / "video"
# traffic-density-analysis-system/data/output/
OUTPUT_FOLDER = PROJECT_ROOT / "data" / "output"

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


@router.get("/videos/outputs")
def list_output_videos():
    """
    List all videos inside the data/output directory
    """
    if not OUTPUT_FOLDER.exists():
        return []
    
    # Return names of all .mp4 files in data/output
    videos = [f.name for f in OUTPUT_FOLDER.glob("*.mp4") if f.is_file()]
    videos.sort()
    return videos


@router.get("/video")
def get_video(
    request: Request,
    camera_id: str | None = None,
    video_name: str | None = None
):
    selected_video = "cam01-traffic3_output.mp4"
    if video_name:
        selected_video = video_name
    elif camera_id:
        if camera_id.lower() == "cam01":
            selected_video = "cam01-traffic3_output.mp4"
        elif camera_id.lower() == "cam02":
            selected_video = "cam02-traffic8_output.mp4"
        elif camera_id.lower() == "cam03":
            selected_video = "cam03-traffic1_output.mp4"
        else:
            selected_video = f"{camera_id.lower()}-traffic3_output.mp4"

    # Đảm bảo video kết thúc bằng _output.mp4 (Bắt buộc phải là video kết quả)
    if selected_video.endswith(".mp4") and not selected_video.endswith("_output.mp4"):
        selected_video = selected_video.replace(".mp4", "_output.mp4")

    # BẮT BUỘC CHỈ LẤY TRONG THƯ MỤC data/output
    file_path = OUTPUT_FOLDER / selected_video
    
    # Nếu file yêu cầu cụ thể không tồn tại, thử lấy file đầu tiên trong data/output
    if not (file_path.exists() and file_path.is_file()):
        all_outputs = list(OUTPUT_FOLDER.glob("*.mp4"))
        if all_outputs:
            file_path = all_outputs[0]
            print(f"[Strict-Output] Không thấy file {selected_video}, dùng file đầu tiên trong data/output: {file_path}")
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Bắt buộc phải phát video từ data/output nhưng không tìm thấy tệp .mp4 nào tại {OUTPUT_FOLDER}"
            )

    # ================= DEBUG =================
    print("PROJECT_ROOT:", PROJECT_ROOT)
    print("OUTPUT_FOLDER:", OUTPUT_FOLDER)
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