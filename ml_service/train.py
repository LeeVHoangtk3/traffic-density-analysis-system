import os
import pandas as pd
from traffic_predictor import TrafficPredictor

def main():
    print("=" * 60)
    print("MÔ ĐUN HUẤN LUYỆN MÔ HÌNH DỰ BÁO LƯU LƯỢNG (TRAIN)")
    print("=" * 60)
    
    # Đường dẫn lưu mô hình (đặt ngay trong thư mục ml_service)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, 'model.pkl')
    
    # 1. Khởi tạo predictor
    predictor = TrafficPredictor(model_path=model_path)
    
    # 2. Sinh dữ liệu giả lập (hoặc bạn có thể load từ CSV/Database thật ở đây)
    # Ví dụ: raw_history = pd.read_csv('your_real_traffic_data.csv')
    days_to_simulate = 60
    raw_history = predictor.generate_dummy_data(days=days_to_simulate)
    
    print(f"\n[Dữ liệu huấn luyện]: Lấy {len(raw_history)} dòng ({days_to_simulate} ngày)")
    print(raw_history.head())
    
    # 3. Đánh giá chất lượng và Train Model
    print("\n[*] Đang tiến hành trích xuất đặc trưng và chia tập Validation...")
    predictor.train_and_evaluate(raw_history)
    
    # 4. Lưu lại mô hình vào file .pkl
    predictor.save_model()
    
    if os.path.exists(model_path):
        print(f"\n=> OK: Quá trình huấn luyện hoàn tất. Mô hình sẵn sàng phục vụ tại: {model_path}")
    else:
        print("\n=> LỖI: Không tìm thấy file mô hình sau khi lưu.")

if __name__ == "__main__":
    main()
