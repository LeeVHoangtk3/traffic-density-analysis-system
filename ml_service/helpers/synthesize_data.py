import os
import sys
import pandas as pd
import numpy as np

def get_hourly_factor(hour, is_weekend=False):
    # Hệ số sinh học theo giờ đô thị thực tế
    if 23 <= hour or hour <= 5:  # Ban đêm (Giờ thấp điểm cực độ)
        return np.random.uniform(0.06, 0.15) if not is_weekend else np.random.uniform(0.08, 0.18)
    elif hour == 6:  # Sáng sớm
        return np.random.uniform(0.35, 0.45)
    elif 7 <= hour <= 9:  # Cao điểm sáng
        # Cuối tuần cao điểm sáng muộn hơn và thấp hơn
        return np.random.uniform(0.50, 0.65) if is_weekend else np.random.uniform(0.85, 1.00)
    elif 10 <= hour <= 16:  # Ban ngày bình thường
        return np.random.uniform(0.55, 0.70)
    elif 17 <= hour <= 19:  # Cao điểm chiều
        return np.random.uniform(0.60, 0.75) if is_weekend else np.random.uniform(0.85, 1.00)
    else:  # Tối muộn (20h-22h)
        return np.random.uniform(0.40, 0.55)

def generate_synthetic_row(segment_id, timestamp):
    hour = timestamp.hour
    day_of_week = timestamp.dayofweek
    is_weekend = (day_of_week >= 5)
    
    # 1. Định nghĩa công suất đỉnh và tỷ lệ làn đường
    if segment_id == 138:
        columns = ['vol_straight', 'vol_left', 'vol_right']
        weights = {'vol_straight': 0.60, 'vol_left': 0.23, 'vol_right': 0.17}
        v_max_peak = 550
    elif segment_id == 72887:
        columns = ['vol_straight', 'vol_left']
        weights = {'vol_straight': 0.70, 'vol_left': 0.30}
        v_max_peak = 450
    elif segment_id == 83624:
        columns = ['vol_straight', 'vol_left']
        weights = {'vol_straight': 0.65, 'vol_left': 0.35}
        v_max_peak = 350
    else:
        columns = ['vol_straight', 'vol_left', 'vol_right']
        weights = {'vol_straight': 0.60, 'vol_left': 0.23, 'vol_right': 0.17}
        v_max_peak = 550
        
    # 2. Tính toán tổng lưu lượng mục tiêu V_total
    factor = get_hourly_factor(hour, is_weekend)
    v_target = v_max_peak * factor
    
    # Giả định ngẫu nhiên 5% khả năng có thời tiết xấu (mưa to) hoặc sự cố làm giảm lưu lượng 20-30%
    if np.random.rand() < 0.05:
        weather_factor = np.random.uniform(0.70, 0.80)
        v_target *= weather_factor
        
    v_min = max(10, int(v_target * 0.90))
    v_max = max(15, int(v_target * 1.10))
    v_total = np.random.randint(v_min, v_max + 1)
    
    # 3. Phân bổ lưu lượng vào các làn đường theo tỷ lệ hình học
    # Thêm nhiễu ngẫu nhiên hành vi lái xe đô thị: +-5% đến +-10%
    noisy_weights = {}
    for col in columns:
        sign = 1 if np.random.rand() > 0.5 else -1
        noise = sign * np.random.uniform(0.05, 0.10)
        noisy_weights[col] = weights[col] * (1.0 + noise)
        
    # Chuẩn hóa lại trọng số
    sum_noisy = sum(noisy_weights.values())
    norm_weights = {col: w / sum_noisy for col, w in noisy_weights.items()}
    
    # Phân bổ lượng xe làm tròn số nguyên không âm
    allocated = {}
    for col in columns:
        allocated[col] = max(0, int(round(v_total * norm_weights[col])))
        
    # Bù trừ sai số làm tròn để đảm bảo tổng đúng bằng v_total
    diff = v_total - sum(allocated.values())
    if diff != 0 and columns:
        highest_col = max(columns, key=lambda c: weights[c])
        allocated[highest_col] = max(0, allocated[highest_col] + diff)
        
    # Tạo row kết quả
    result_row = {
        'timestamp': timestamp,
        'segment_id': segment_id,
        'vol_straight': allocated.get('vol_straight', 0),
        'vol_left': allocated.get('vol_left', 0),
        'vol_right': allocated.get('vol_right', 0)
    }
    
    # 4. Đối với Segment 2 làn (72887, 83624), sinh lưu lượng rẽ phải phụ thấp theo giờ
    if segment_id in [72887, 83624]:
        if 6 <= hour <= 22:
            result_row['vol_right'] = np.random.randint(5, 16)
        else:
            result_row['vol_right'] = np.random.randint(0, 5)
            
    # 5. Kiểm tra và bắt buộc tuân thủ nghiêm ngặt phân cấp: Straight > Left > Right
    # Trong trường hợp hiếm hoi bị sai lệch do làm tròn hoặc nhiễu lớn, ta chủ động sửa lại
    s_val = result_row['vol_straight']
    l_val = result_row['vol_left']
    r_val = result_row['vol_right']
    
    if l_val >= s_val:
        # Tăng thẳng hoặc giảm trái để đảm bảo Straight > Left
        result_row['vol_straight'] = int(l_val * 1.2) + 1
    if r_val >= result_row['vol_left']:
        # Tăng trái hoặc giảm phải để đảm bảo Left > Right
        result_row['vol_left'] = int(r_val * 1.2) + 1
        # Đảm bảo Straight vẫn lớn hơn Left sau khi điều chỉnh Left
        if result_row['vol_left'] >= result_row['vol_straight']:
            result_row['vol_straight'] = int(result_row['vol_left'] * 1.2) + 1
            
    return result_row

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
        
    print("[*] Khởi động tiến trình Tăng cường & Tổng hợp dữ liệu giao thông lớn nâng cao...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, "data", "junction_pivot_clean.csv")
    
    if not os.path.exists(csv_path):
        print(f"[!] Lỗi: Không tìm thấy tệp {csv_path}. Hãy chạypreprocess.py và augment_data.py trước.")
        sys.exit(1)
        
    df_orig = pd.read_csv(csv_path)
    df_orig['timestamp'] = pd.to_datetime(df_orig['timestamp'])
    print(f" -> Dữ liệu gốc hiện có: {len(df_orig):,} dòng")
    
    # Xác định khoảng thời gian sinh thêm dữ liệu mô phỏng liên tục
    # Sinh dữ liệu 365 ngày của năm 2026 (nối tiếp tuyệt đẹp vào tương lai, dữ liệu gốc kéo dài đến hết 2025)
    start_date = pd.to_datetime("2026-01-01 00:00:00")
    end_date = pd.to_datetime("2026-12-31 23:45:00")
    
    time_index = pd.date_range(start=start_date, end=end_date, freq='15min')
    print(f" -> Lập kế hoạch sinh 365 ngày dữ liệu 15 phút: {len(time_index):,} mốc thời gian")
    
    segments = [138, 72887, 83624]
    synthetic_rows = []
    
    print(" -> Đang tiến hành mô phỏng nhịp sinh học và tạo dữ liệu tổng hợp cho 3 phân đoạn...")
    for seg_id in segments:
        print(f"    * Đang tạo dữ liệu cho Segment {seg_id}...")
        for ts in time_index:
            row = generate_synthetic_row(seg_id, ts)
            synthetic_rows.append(row)
            
    df_synth = pd.DataFrame(synthetic_rows)
    print(f" -> Đã tạo thành công {len(df_synth):,} dòng dữ liệu mô phỏng chất lượng cao.")
    
    # Hợp nhất dữ liệu gốc và dữ liệu sinh thêm
    print(" -> Đang gộp dữ liệu và lưu trữ...")
    df_merged = pd.concat([df_orig, df_synth], ignore_index=True)
    df_merged = df_merged.sort_values(['timestamp', 'segment_id']).reset_index(drop=True)
    
    # Đảm bảo định dạng kiểu số nguyên cho các cột lưu lượng xe
    lanes = ['vol_straight', 'vol_left', 'vol_right']
    for col in lanes:
        df_merged[col] = df_merged[col].round().astype(int)
        
    df_merged.to_csv(csv_path, index=False)
    
    print("\n" + "="*70)
    print(" [+] TIẾN TRÌNH TỔNG HỢP DỮ LIỆU ĐÃ HOÀN THÀNH XUẤT SẮC!")
    print(f"     - Kích thước tệp dữ liệu sạch ban đầu: {len(df_orig):,} dòng")
    print(f"     - Kích thước dữ liệu sinh thêm (mô phỏng): {len(df_synth):,} dòng")
    print(f"     - Tổng số dòng sau khi hợp nhất: {len(df_merged):,} dòng")
    print(f"     - Trạng thái tệp đã cập nhật: {csv_path}")
    print("     - Thống kê lưu lượng sau tăng cường quy mô lớn:")
    print(df_merged[lanes].describe())
    print("="*70)

if __name__ == '__main__':
    main()
