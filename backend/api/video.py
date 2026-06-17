from pathlib import Path
import json
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from backend.services.db_service import get_db

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


@router.get("/video/metadata")
def get_video_metadata(video_name: str, db=Depends(get_db)):
    """
    Get or dynamically generate/cache second-by-second vehicle counts
    for the requested video file without overwriting any live database.
    """
    json_name = video_name.replace(".mp4", ".json")
    file_path = OUTPUT_FOLDER / json_name
    
    if file_path.exists() and file_path.is_file():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Metadata] Error reading {file_path}: {e}")
            
    # Auto-detect camera ID from the video name
    match = re.search(r"^(cam\d+)", video_name, re.IGNORECASE)
    camera_id = match.group(1).lower() if match else "cam01"
    
    # Query all detections for this camera, ordered by time ascending
    detections = list(
        db.vehicle_detections.find({"camera_id": camera_id})
        .sort("timestamp", 1)
    )
    
    if not detections:
        # Fallback empty timeline
        return {
            "video_name": video_name,
            "camera_id": camera_id,
            "timeline": {
                "0": {"car": 0, "motorcycle": 0, "truck": 0, "bus": 0}
            }
        }
        
    first_ts = detections[0]["timestamp"]
    
    def parse_ts(t):
        if isinstance(t, datetime):
            return t
        try:
            return datetime.fromisoformat(str(t).replace("Z", "+00:00"))
        except Exception:
            try:
                return datetime.strptime(str(t), "%Y-%m-%dT%H:%M:%S.%f")
            except Exception:
                return datetime.utcnow()
                
    start_dt = parse_ts(first_ts)
    
    # Build cumulative second-by-second timeline
    timeline = {}
    running_counts = {"car": 0, "motorcycle": 0, "truck": 0, "bus": 0}
    
    detections_by_sec = {}
    max_sec = 0
    
    for d in detections:
        dt = parse_ts(d["timestamp"])
        sec_offset = int((dt - start_dt).total_seconds())
        if sec_offset < 0:
            sec_offset = 0
        if sec_offset > 7200:  # 2 hours ceiling for safety
            continue
        if sec_offset > max_sec:
            max_sec = sec_offset
            
        vtype = str(d.get("vehicle_type") or "car").lower()
        if vtype not in running_counts:
            if "motor" in vtype:
                vtype = "motorcycle"
            elif "truck" in vtype:
                vtype = "truck"
            elif "bus" in vtype:
                vtype = "bus"
            else:
                vtype = "car"
                
        if sec_offset not in detections_by_sec:
            detections_by_sec[sec_offset] = []
        detections_by_sec[sec_offset].append(vtype)
        
    for s in range(max_sec + 1):
        if s in detections_by_sec:
            for vtype in detections_by_sec[s]:
                running_counts[vtype] = running_counts.get(vtype, 0) + 1
        timeline[str(s)] = dict(running_counts)
        
    metadata = {
        "video_name": video_name,
        "camera_id": camera_id,
        "timeline": timeline
    }
    
    # Cache metadata JSON alongside output video
    try:
        if OUTPUT_FOLDER.exists():
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            print(f"[Metadata] Cached new timeline JSON to {file_path}")
    except Exception as e:
        print(f"[Metadata] Failed to write cache {file_path}: {e}")
        
    return metadata


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
            selected_video = "cam02-traffic5_output.mp4"
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