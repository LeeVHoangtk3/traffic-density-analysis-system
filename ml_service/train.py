import os
import pandas as pd
from traffic_predictor import TrafficPredictor

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, 'model.pkl')
    csv_path = os.path.join(current_dir, 'data', 'traffic_data.csv') # Đường dẫn file Kaggle

    predictor = TrafficPredictor(model_path=model_path)

    print("[*] Đang đọc dữ liệu từ Dataset Kaggle...")
    # 1. Đọc dữ liệu từ CSV
    df_raw = pd.read_csv(csv_path)

    # 2. Chuẩn hóa tên cột để khớp với class TrafficPredictor
    # Dataset Kaggle có cột 'date_time' và 'traffic_volume'
    df = pd.DataFrame()
    df['timestamp'] = pd.to_datetime(df_raw['date_time'])
    df['vehicle_count'] = df_raw['traffic_volume']

    print(f" -> Đã tải {len(df)} dòng dữ liệu.")

    # 3. Huấn luyện
    predictor.train_and_evaluate(df)

    # 4. Lưu mô hình
    predictor.save_model()
    print("="*50)
    print("XONG! File model.pkl đã sẵn sàng.")

if __name__ == "__main__":
    main()