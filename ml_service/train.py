import os
import pandas as pd
from ml_service.traffic_predictor import TrafficPredictor

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, 'model.pkl')
    csv_path = os.path.join(current_dir, 'data', 'urban_traffic.csv')

    predictor = TrafficPredictor(model_path=model_path)

    print("[*] Đang đọc dữ liệu từ Dataset urban_traffic.csv...")
    df_raw = pd.read_csv(csv_path)

    print(f"    -> Các cột trong file: {list(df_raw.columns)}")

    # Chuẩn hoá tên cột:
    # urban_traffic.csv có cột 'Timestamp' và 'Vehicle_Count'
    df = pd.DataFrame()
    df['timestamp'] = pd.to_datetime(df_raw['Timestamp'])
    df['vehicle_count'] = df_raw['Vehicle_Count'].astype(int)

    # Sắp xếp theo thời gian tăng dần
    df = df.sort_values('timestamp').reset_index(drop=True)

    print(f"    -> Đã tải {len(df)} dòng dữ liệu.")
    print(f"    -> Khoảng thời gian: {df['timestamp'].min()} đến {df['timestamp'].max()}")
    print(f"    -> Trung bình xe/15p: {df['vehicle_count'].mean():.1f}")
    print(f"    -> Min: {df['vehicle_count'].min()} | Max: {df['vehicle_count'].max()}")

    # Huấn luyện
    predictor.train_and_evaluate(df)

    # Lưu mô hình
    predictor.save_model()
    print("=" * 50)
    print("XONG! File model.pkl đã sẵn sàng với dữ liệu thực 15 phút.")

if __name__ == "__main__":
    main()