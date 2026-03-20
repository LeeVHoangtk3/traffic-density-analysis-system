import pandas as pd
from traffic_predictor import TrafficPredictor

import os

def main():
    print("=" * 60)
    print("HỆ THỐNG DỰ BÁO LƯU LƯỢNG GIAO THÔNG (MODULE C - THỜI GIAN THỰC)")
    print("=" * 60)
    
    # 1. Khởi tạo predictor
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, 'model.pkl')
    predictor = TrafficPredictor(model_path=model_path)
    
    # Do module đã được huấn luyện bên train.py, mô hình chỉ cần Load hệ trọng số
    try:
        if not predictor.load_model():
            print("❌ Lỗi: Không thể tải mô hình. Bạn đã chạy 'python ml_service/train.py' chưa?")
            return
    except Exception as e:
        print(f"Lỗi: {e}")
        return
        
    print("[+] Tải mô hình XGBoost thành công!")
    print("\n[*] KHỞI ĐỘNG MODULE PREDICT CHO 15 PHÚT TIẾP THEO...")
    
    # ==============================================================
    # Trong MÔI TRƯỜNG THỰC TẾ:
    # Ở đây, bạn sẽ pull dữ liệu từ Database (MySQL, MongoDB) 
    # Mảng này chứa TỐI THIỂU 3 quan trắc lịch sử sát sườn nhất của camera AI
    # ==============================================================
    
    # DEMO: Ta sinh lại vài dòng dữ liệu để giả lập "Lịch sử 45 phút gần nhất"
    demo_data_stream = predictor.generate_dummy_data(days=1).tail(5)
    
    current_time = demo_data_stream['timestamp'].iloc[-1]
    
    print(f"\n-> Nhận dòng dữ liệu Camera theo thời gian thực (Lịch sử gần nhất):")
    for _, row in demo_data_stream.tail(3).iterrows():
        print(f"      Thời gian: {row['timestamp'].strftime('%Y-%m-%d %H:%M')} | Lưu lượng: {row['vehicle_count']} xe")
        
    # Gọi hàm predict cho tương lai (trả về 1 con số nguyên duy nhất)
    # Hàm này tự động sinh các feature như Lag, TimeSeries cho dòng dữ liệu mới
    forecast = predictor.predict(demo_data_stream)
    
    next_time = current_time + pd.Timedelta(minutes=15)
    print(f"\n 🔮 KẾT QUẢ DỰ BÁO:")
    print(f" -> Khung giờ [{next_time.strftime('%Y-%m-%d %H:%M')}] sẽ có ĐẠT KHOẢNG: {forecast} xe lưu thông.")
    print("=" * 60)

if __name__ == "__main__":
    main()
