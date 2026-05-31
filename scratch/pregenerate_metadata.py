import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

# Khắc phục lỗi mã hóa Unicode hiển thị tiếng Việt trên Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.mongo_database import db

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

def main():
    print("[*] Starting timeline metadata generation for existing output videos...")
    output_dir = Path(PROJECT_ROOT) / "data" / "output"
    
    if not output_dir.exists():
        print(f"[!] Output directory {output_dir} does not exist!")
        return
        
    videos = list(output_dir.glob("*.mp4"))
    print(f"[*] Found {len(videos)} video files in {output_dir}")
    
    for video in videos:
        video_name = video.name
        json_name = video.with_suffix(".json")
        
        match = re.search(r"^(cam\d+)", video_name, re.IGNORECASE)
        camera_id = match.group(1).lower() if match else "cam01"
        
        print(f"[*] Processing {video_name} (Camera: {camera_id})...")
        
        # Query detections
        detections = list(
            db.vehicle_detections.find({"camera_id": camera_id})
            .sort("timestamp", 1)
        )
        
        if not detections:
            print(f"    [!] No database detections found for camera {camera_id}. Creating fallback timeline.")
            metadata = {
                "video_name": video_name,
                "camera_id": camera_id,
                "timeline": {
                    "0": {"car": 0, "motorcycle": 0, "truck": 0, "bus": 0}
                }
            }
        else:
            first_ts = detections[0]["timestamp"]
            start_dt = parse_ts(first_ts)
            
            timeline = {}
            running_counts = {"car": 0, "motorcycle": 0, "truck": 0, "bus": 0}
            
            detections_by_sec = {}
            max_sec = 0
            
            for d in detections:
                dt = parse_ts(d["timestamp"])
                sec_offset = int((dt - start_dt).total_seconds())
                if sec_offset < 0:
                    sec_offset = 0
                if sec_offset > 7200:
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
            
        # Write JSON
        try:
            with open(json_name, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            print(f"    [+] Saved timeline JSON to {json_name.name}")
        except Exception as e:
            print(f"    [!] Failed to save timeline JSON: {e}")
            
    print("[*] Done!")

if __name__ == '__main__':
    main()
