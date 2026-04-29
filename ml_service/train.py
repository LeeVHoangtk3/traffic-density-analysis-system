import os
import pandas as pd
from ml_service.traffic_predictor import TrafficPredictor
from ml_service.light_delta_model import LightDeltaModel
from ml_service.label_generator import generate_delta_labels

def main():
    base = os.path.dirname(__file__)
    raw_csv = os.path.join(base, 'data/urban_traffic.csv')
    delta_csv = os.path.join(base, 'data/training_data_delta.csv')
    
    # 1. Tạo nhãn
    generate_delta_labels(raw_csv, delta_csv)
    df_delta = pd.read_csv(delta_csv)
    df_delta['timestamp'] = pd.to_datetime(df_delta['timestamp'])

    # 2. Huấn luyện Model 1: Dự báo số xe (TrafficPredictor)
    print("\n--- Training Model 1: Vehicle Forecast ---")
    predictor = TrafficPredictor(os.path.join(base, 'model.pkl'))
    # Chuẩn bị format cho model 1 (dùng code cũ của bạn)
    df_m1 = df_delta[['timestamp', 'inbound_count']].rename(columns={'inbound_count': 'vehicle_count'})
    predictor.train_and_evaluate(df_m1)
    predictor.save_model()

    # 3. Huấn luyện Model 2: Đề xuất đèn (LightDeltaModel)
    print("\n--- Training Model 2: Light Delta ---")
    light_model = LightDeltaModel(os.path.join(base, 'light_model.pkl'))
    light_model.train(df_delta)

if __name__ == "__main__":
    main()