import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from sklearn.cluster import KMeans

# Fix the import path to allow running from terminal using python -m ml_service.density_cluster
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from backend.mongo_database import db

def load_data_from_db(camera_id: str) -> pd.DataFrame:
    try:
        cursor = db.traffic_aggregation.find({"camera_id": camera_id}).sort("timestamp", 1)
        data = list(cursor)
        if len(data) > 0:
            return pd.DataFrame(data)
    except Exception as e:
        print(f"Error loading from DB: {e}")
    return pd.DataFrame()

def load_data_from_csv() -> pd.DataFrame:
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "junction_pivot_clean.csv")
    try:
        if os.path.exists(csv_path):
            return pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error loading CSV: {e}")
    return pd.DataFrame()

def process_clustering_for_dataframe(camera_id: str, df: pd.DataFrame):
    directions = ["straight", "left", "right"]
    
    # Check if necessary columns exist
    has_data = not df.empty
    if has_data:
        # Rename columns if they lack 'vol_' prefix (mostly for CSV fallback)
        rename_map = {}
        for d in directions:
            if d in df.columns and f"vol_{d}" not in df.columns:
                rename_map[d] = f"vol_{d}"
        if rename_map:
            df = df.rename(columns=rename_map)
            
        for d in directions:
            if f"vol_{d}" not in df.columns:
                print(f"Warning: Column vol_{d} not found for {camera_id}. Skipping.")
                continue
    else:
        print(f"No data for {camera_id}. Skipping.")
        return
        
    for direction in directions:
        col_name = f"vol_{direction}"
        if col_name not in df.columns:
            continue
            
        # Extract 1D array
        V_D = df[col_name].dropna().values.reshape(-1, 1)
        
        if len(V_D) < 4 or len(np.unique(V_D)) < 4:
            print(f"Not enough unique data points to cluster {direction} for {camera_id}. Need at least 4.")
            continue
            
        # Run KMeans
        kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
        kmeans.fit(V_D)
        
        # Get centroids and sort them
        centroids = kmeans.cluster_centers_.flatten()
        centroids.sort()
        
        C0, C1, C2, C3 = centroids
        
        # Calculate thresholds
        T1 = (C0 + C1) / 2.0
        T2 = (C1 + C2) / 2.0
        T3 = (C2 + C3) / 2.0
        
        # Round values for cleaner storage
        centroids_list = [float(round(c, 2)) for c in centroids]
        T1 = float(round(T1, 2))
        T2 = float(round(T2, 2))
        T3 = float(round(T3, 2))
        
        # Construct document
        document = {
            "camera_id": camera_id,
            "direction": direction,
            "thresholds": {
                "low_to_medium": T1,
                "medium_to_high": T2,
                "high_to_heavy": T3
            },
            "centroids": centroids_list,
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Save to MongoDB
        try:
            db.directional_thresholds.update_one(
                {"camera_id": camera_id, "direction": direction},
                {"$set": document},
                upsert=True
            )
            print(f"Successfully updated thresholds for {camera_id} - {direction}.")
            print(f"  Centroids: {centroids_list}")
            print(f"  Thresholds: T1={T1}, T2={T2}, T3={T3}")
        except Exception as e:
            print(f"Error saving to MongoDB for {direction} ({camera_id}): {e}")

def run_clustering():
    print("[*] Bắt đầu tiến trình phân cụm (Clustering) ngưỡng lưu lượng...")
    
    # 1. Attempt to load from DB and find all distinct cameras
    try:
        camera_ids = db.traffic_aggregation.distinct("camera_id")
        if camera_ids:
            print(f" -> Tìm thấy {len(camera_ids)} camera(s) trong DB: {camera_ids}")
            for cam_id in camera_ids:
                print(f"\n--- Đang xử lý phân cụm cho Camera: {cam_id} (Dữ liệu DB) ---")
                df = load_data_from_db(cam_id)
                process_clustering_for_dataframe(cam_id, df)
            return  # Nếu DB có data thì dùng DB, không cần fallback
    except Exception as e:
        print(f"Lỗi khi truy vấn danh sách camera từ DB: {e}")

    # 2. Fallback to CSV if DB is empty or failed
    print("\n[!] Dữ liệu DB trống hoặc thiếu. Đang chuyển sang đọc từ CSV dự phòng...")
    df_csv = load_data_from_csv()
    
    if df_csv.empty:
        print("Không có dữ liệu CSV để phân cụm. Kết thúc.")
        return
        
    # Check if 'segment_id' exists to group by segments
    if 'segment_id' in df_csv.columns:
        segments = df_csv['segment_id'].unique()
        print(f" -> Tìm thấy {len(segments)} segment_id(s) trong CSV: {segments}")
        for seg_id in segments:
            cam_id = str(seg_id)
            print(f"\n--- Đang xử lý phân cụm cho Segment: {cam_id} (Dữ liệu CSV) ---")
            df_seg = df_csv[df_csv['segment_id'] == seg_id].copy()
            process_clustering_for_dataframe(cam_id, df_seg)
    else:
        # Fallback if no segment_id
        print("\n--- Đang xử lý phân cụm cho toàn bộ dữ liệu CSV (Mặc định: CAM_01) ---")
        process_clustering_for_dataframe("CAM_01", df_csv)

if __name__ == "__main__":
    run_clustering()
