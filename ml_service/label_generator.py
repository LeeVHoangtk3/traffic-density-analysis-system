import pandas as pd
import os

def generate_delta_labels(csv_input, csv_output):
    df = pd.read_csv(csv_input)
    df['timestamp'] = pd.to_datetime(df['Timestamp'])
    df = df.sort_values('timestamp')

    # Tính Queue Proxy = Lưu lượng hiện tại - Lưu lượng 15p trước
    # Vì camera 1 hướng nên vehicle_count chính là inbound_count
    df['inbound_count'] = df['Vehicle_Count']
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