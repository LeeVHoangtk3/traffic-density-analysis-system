import pandas as pd
import os

# ============================================================
# CHIẾN THUẬT: SCALE DATA (Tỉ lệ hóa dữ liệu)
#
# VẤN ĐỀ:
#   - Dataset CSV (urban_traffic.csv): Vehicle_Count trung bình ≈ 50 xe / 15 phút
#   - Thực tế DB (traffic_aggregation):  vehicle_count trung bình ≈ 111 xe / 15 phút
#   → Dataset THẤP HƠN thực tế gần 2.2 lần → model học sai → dự báo ra ~41, thực tế >100
#
# GIẢI PHÁP:
#   Nhân Vehicle_Count trong CSV với SCALE_FACTOR để kéo dữ liệu training
#   lên khớp với phân phối thực tế.
#
#   SCALE_FACTOR = mean_thực_tế / mean_dataset
#               = 111 / 50.2
#               ≈ 2.21
#
# CÁCH ĐIỀU CHỈNH:
#   - Model dự báo VẪN THẤP HƠN thực tế → tăng SCALE_FACTOR lên
#   - Model dự báo CAO HƠN thực tế      → giảm SCALE_FACTOR xuống
# ============================================================
SCALE_FACTOR = 111.0 / 50.2   # ≈ 2.21  ← Đây là tỉ lệ thực tế / dataset

def generate_delta_labels(csv_input, csv_output):
    df = pd.read_csv(csv_input)
    df['timestamp'] = pd.to_datetime(df['Timestamp'])
    df = df.sort_values('timestamp')

    # Tính Queue Proxy = Lưu lượng hiện tại - Lưu lượng 15p trước
    # Vì camera 1 hướng nên vehicle_count chính là inbound_count
    # Áp dụng SCALE_FACTOR để căn chỉnh dữ liệu về thực tế
    df['inbound_count'] = (df['Vehicle_Count'] * SCALE_FACTOR).round().astype(int)
    df['queue_proxy'] = df['inbound_count'].diff().fillna(0)

    # Logic tạo nhãn Delta Green (Heuristic Rules)
    def calculate_delta(proxy):
        if proxy > 15:   return 30  # Tắc nặng -> Tăng 30s
        if proxy > 5:    return 15  # Hơi đông -> Tăng 15s
        if proxy < -15:  return -30 # Đường vắng cực nhanh -> Giảm 30s
        if proxy < -5:   return -15 # Đường bắt đầu thoáng -> Giảm 15s
        return 0                    # Ổn định -> Giữ nguyên

    df['delta_green'] = df['queue_proxy'].apply(calculate_delta)
    
    # Thêm các đặc trưng thời gian
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['is_peak_hour'] = df['hour'].apply(lambda x: 1 if (7<=x<=9 or 17<=x<=19) else 0)

    # Lưu file training mới
    df.to_csv(csv_output, index=False)
    print(f" Đã tạo dữ liệu huấn luyện đèn tại: {csv_output}")

if __name__ == "__main__":
    base = os.path.dirname(__file__)
    generate_delta_labels(os.path.join(base, 'data/urban_traffic.csv'), 
                          os.path.join(base, 'data/training_data_delta.csv'))