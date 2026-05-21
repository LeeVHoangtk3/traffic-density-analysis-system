import os
import pandas as pd
from ml_service.traffic_predictor import TrafficPredictor

# Data file path
# We will use SegmentID 72887 as it has the most records
SEGMENT_ID = "72887"

def main():
    base = os.path.dirname(__file__)
    raw_csv = os.path.join(base, 'data/Automated_Traffic_Volume_Counts_20260521.csv')

    print("[1] Đọc dữ liệu từ CSV (NYC Automated Traffic Volume)...")
    df = pd.read_csv(raw_csv, dtype={'SegmentID': str})
    print(f"    Tổng số record gốc: {len(df)}")
    
    print(f"[2] Lọc SegmentID {SEGMENT_ID} và dọn dẹp dữ liệu...")
    df = df[df['SegmentID'] == SEGMENT_ID].copy()
    
    # Chuyển đổi kiểu dữ liệu
    df['Vol'] = pd.to_numeric(df['Vol'], errors='coerce')
    df['MM'] = pd.to_numeric(df['MM'], errors='coerce')
    df = df.dropna(subset=['Vol', 'MM']).copy()
    
    # Lọc các khoảng 15 phút (0, 15, 30, 45)
    df = df[df['MM'].isin([0, 15, 30, 45])].copy()
    
    # Lọc giá trị Vol rác (âm)
    df = df[df['Vol'] >= 0].copy()
    
    # Tạo timestamp
    df['timestamp'] = pd.to_datetime(
        df['Yr'].astype(str) + '-' + 
        df['M'].astype(str).str.zfill(2) + '-' + 
        df['D'].astype(str).str.zfill(2) + ' ' + 
        df['HH'].astype(str).str.zfill(2) + ':' + 
        df['MM'].astype(str).str.zfill(2)
    )
    
    df = df.rename(columns={'Vol': 'vehicle_count'})
    df = df[['timestamp', 'vehicle_count']].sort_values('timestamp').reset_index(drop=True)
    
    print(f"    Số lượng bản ghi sau khi lọc: {len(df)}")
    print(f"    Trung bình vehicle_count: {df['vehicle_count'].mean():.1f} xe/15p")

    print("\n--- Training Model: Vehicle Forecast + Density Level ---")
    predictor = TrafficPredictor(os.path.join(base, 'model.pkl'))
    predictor.train_and_evaluate(df)
    predictor.save_model()


if __name__ == "__main__":
    main()