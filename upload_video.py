import os
import requests
import math

def upload_in_chunks(file_path, url, chunk_size=5 * 1024 * 1024):
    """
    Upload file in chunks to the backend.
    
    :param file_path: Path to the file to upload.
    :param url: Backend upload endpoint URL.
    :param chunk_size: Size of each chunk in bytes (default 5MB).
    """
    file_size = os.path.getsize(file_path)
    total_chunks = math.ceil(file_size / chunk_size)
    filename = os.path.basename(file_path)
    
    print(f"Uploading {filename} ({file_size} bytes) in {total_chunks} chunks...")

    with open(file_path, 'rb') as f:
        for i in range(total_chunks):
            chunk_data = f.read(chunk_size)
            
            # Prepare multipart/form-data
            files = {
                'file': (filename, chunk_data, 'application/octet-stream')
            }
            data = {
                'filename': filename,
                'chunk_index': i,
                'total_chunks': total_chunks
            }
            
            response = requests.post(url, files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if result['status'] == 'completed':
                    print(f"Chunk {i+1}/{total_chunks}: SUCCESS (Finalized)")
                else:
                    print(f"Chunk {i+1}/{total_chunks}: SUCCESS")
            else:
                print(f"Chunk {i+1}/{total_chunks}: FAILED ({response.status_code})")
                print(response.text)
                return

    print("Upload completed successfully!")

if __name__ == "__main__":
    # Path to the output video
    VIDEO_PATH = "videos/output.mp4"
    UPLOAD_URL = "http://127.0.0.1:8000/video/upload"

    if os.path.exists(VIDEO_PATH):
        upload_in_chunks(VIDEO_PATH, UPLOAD_URL)
    else:
        print(f"File not found: {VIDEO_PATH}")
