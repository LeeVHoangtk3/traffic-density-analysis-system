import cv2
import os
from pathlib import Path

def transcode_video(file_path: Path):
    print(f"\n=========================================")
    print(f"Start transcoding: {file_path.name}")
    print(f"=========================================")
    
    # 1. Open source video
    cap = cv2.VideoCapture(str(file_path))
    if not cap.isOpened():
        print(f"Error: Could not open video {file_path}")
        return False
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Video Info: FPS={fps}, Size={w}x{h}, Total Frames={total_frames}")
    
    # 2. Create temporary file path
    temp_path = file_path.parent / f"temp_{file_path.name}"
    
    # 3. Create VideoWriter with avc1 (H.264) codec
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter(str(temp_path), fourcc, fps, (w, h))
    
    if not out.isOpened():
        print("Error: Could not initialize VideoWriter with codec avc1 (H.264).")
        cap.release()
        return False
        
    # 4. Transcode frame by frame
    count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        out.write(frame)
        count += 1
        
        # Print progress every 500 frames
        if count % 500 == 0 or count == total_frames:
            percent = (count / total_frames) * 100
            print(f"Processing: {count}/{total_frames} frames ({percent:.1f}%)")
            
    # Release resources
    cap.release()
    out.release()
    
    # 5. Overwrite original file with transcoded file
    if temp_path.exists() and temp_path.stat().st_size > 0:
        try:
            # Try to delete original first (Windows safety)
            if file_path.exists():
                os.remove(str(file_path))
            os.rename(str(temp_path), str(file_path))
            print(f"Success: Transcoded {file_path.name} to H.264 successfully!")
            return True
        except Exception as e:
            print(f"Error replacing file: {e}")
            if temp_path.exists():
                os.remove(str(temp_path))
            return False
    else:
        print("Error: Transcoded file is corrupted or empty.")
        if temp_path.exists():
            os.remove(str(temp_path))
        return False

def main():
    # Parents[1] since scratch is inside project root
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    OUTPUT_FOLDER = PROJECT_ROOT / "data" / "output"
    
    print(f"PROJECT ROOT: {PROJECT_ROOT}")
    print(f"OUTPUT FOLDER: {OUTPUT_FOLDER}")
    
    if not OUTPUT_FOLDER.exists():
        print(f"Error: Folder does not exist: {OUTPUT_FOLDER}")
        return
        
    mp4_files = list(OUTPUT_FOLDER.glob("*.mp4"))
    print(f"Found {len(mp4_files)} output video files.")
    
    success_count = 0
    for f in mp4_files:
        # Skip temporary files
        if f.name.startswith("temp_"):
            try:
                os.remove(str(f))
            except:
                pass
            continue
            
        success = transcode_video(f)
        if success:
            success_count += 1
            
    print(f"\n=========================================")
    print(f"Finished! Transcoded successfully {success_count}/{len(mp4_files)} videos.")
    print(f"=========================================")

if __name__ == "__main__":
    main()
