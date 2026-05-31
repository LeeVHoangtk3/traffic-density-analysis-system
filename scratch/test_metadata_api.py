import os
import sys
import json

# Keep stdout encoding correct for Vietnamese console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from backend.main import app

def main():
    print("[*] Initializing TestClient for Traffic AI Backend...")
    client = TestClient(app)
    
    video_name = "cam01-traffic3_output.mp4"
    print(f"[*] Testing GET `/video/metadata?video_name={video_name}`...")
    
    try:
        response = client.get(f"/video/metadata?video_name={video_name}")
        print(f"HTTP Status: {response.status_code}")
        assert response.status_code == 200, "API request failed!"
        
        data = response.json()
        print(f"[+] Successfully retrieved metadata JSON!")
        print(f"    Video Name : {data.get('video_name')}")
        print(f"    Camera ID  : {data.get('camera_id')}")
        
        timeline = data.get('timeline', {})
        seconds_keys = list(timeline.keys())
        print(f"    Timeline   : {len(seconds_keys)} seconds of data")
        
        if seconds_keys:
            sample_sec = seconds_keys[min(5, len(seconds_keys)-1)]
            print(f"    Sample sec ({sample_sec}s): {timeline[sample_sec]}")
            
        print("[*] TEST PASSED SUCCESSFULLY!")
    except Exception as e:
        print(f"[!] TEST FAILED: {e}")

if __name__ == '__main__':
    main()
