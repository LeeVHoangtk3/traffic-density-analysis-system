import os
import pandas as pd
from traffic_predictor import TrafficPredictor

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, 'model.pkl')
    predictor = TrafficPredictor(model_path=model_path)

    if not predictor.load_model():
        print("❌ Lỗi: Chưa có file model.pkl. Hãy chạy train.py trước!")
        return

    # GIẢ LẬP: Lấy dữ liệu từ video 5 phút của bạn
    # Ví dụ video 5 phút bạn đếm được 40 xe.
    real_count = 40 
    now = pd.Timestamp.now().floor('15min')

    # Tạo 3 dòng dữ liệu lịch sử để AI có đủ thông tin (Lag1, Lag2)
    demo_data = pd.DataFrame({
        'timestamp': [now - pd.Timedelta(minutes=30), 
                      now - pd.Timedelta(minutes=15), 
                      now],
        'vehicle_count': [real_count - 5, real_count + 2, real_count]
    })

    forecast = predictor.predict(demo_data)

    print("-" * 30)
    print(f"Dữ liệu thực tế từ video: {real_count} xe/5phút")
    print(f"🔮 AI DỰ BÁO 15 PHÚT TỚI: {forecast} xe")
    print("-" * 30)

if __name__ == "__main__":
    main()