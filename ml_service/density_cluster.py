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

def run_clustering():
    camera_id = "CAM_01"
    
    # Attempt to load from DB
    df = load_data_from_db(camera_id)
    
    # Check if necessary columns exist in DB data
    directions = ["straight", "left", "right"]
    has_data = not df.empty
    if has_data:
        # Verify columns exist
        for d in directions:
            if f"vol_{d}" not in df.columns:
                has_data = False
                break
                
    if not has_data:
        print("DB data is missing or incomplete for direction volumes. Falling back to CSV...")
        df = load_data_from_csv()
        
        # Rename columns if they lack 'vol_' prefix
        if not df.empty:
            rename_map = {}
            for d in directions:
                if d in df.columns and f"vol_{d}" not in df.columns:
                    rename_map[d] = f"vol_{d}"
            if rename_map:
                df = df.rename(columns=rename_map)
        
    if df.empty:
        print("No data available to perform clustering. Exiting.")
        return
        
    for direction in directions:
        col_name = f"vol_{direction}"
        if col_name not in df.columns:
            print(f"Warning: Column {col_name} not found in data. Skipping {direction}.")
            continue
            
        # Extract 1D array
        V_D = df[col_name].dropna().values.reshape(-1, 1)
        
        if len(V_D) < 4 or len(np.unique(V_D)) < 4:
            print(f"Not enough unique data points to cluster {direction}. Need at least 4.")
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
            print(f"Error saving to MongoDB for {direction}: {e}")

if __name__ == "__main__":
    run_clustering()
