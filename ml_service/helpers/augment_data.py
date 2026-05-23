import os
import sys
import pandas as pd
import numpy as np

def get_hourly_factor(hour):
    # Thiết lập hệ số nhân lưu lượng động mô phỏng nhịp sinh học đô thị chân thực
    if 23 <= hour or hour <= 5:  # Ban đêm (Thấp điểm cực độ)
        return np.random.uniform(0.08, 0.20)
    elif hour == 6:  # Sáng sớm
        return np.random.uniform(0.40, 0.55)
    elif 7 <= hour <= 9:  # Cao điểm sáng
        return np.random.uniform(0.85, 1.00)
    elif 10 <= hour <= 16:  # Ban ngày bình thường
        return np.random.uniform(0.60, 0.75)
    elif 17 <= hour <= 19:  # Cao điểm chiều
        return np.random.uniform(0.85, 1.00)
    else:  # Tối muộn (20h-22h)
        return np.random.uniform(0.45, 0.60)

def impute_row(row, segment_id, hour=12):
    # Cấu hình hình học làn đường và giới hạn công suất riêng cho từng phân đoạn
    # Segment 138: Ngã 3 tách 3 làn đầy đủ
    # Segment 72887: Trục Đông-Tây (có làn rẽ phải phụ dẫn vào đường gom nội bộ)
    # Segment 83624: Trục Bắc-Nam (có làn rẽ phải phụ dẫn vào đường gom nội bộ)
    
    factor = get_hourly_factor(hour)
    
    if segment_id == 138:
        columns = ['vol_straight', 'vol_left', 'vol_right']
        weights = {'vol_straight': 0.60, 'vol_left': 0.23, 'vol_right': 0.17}
        v_max_peak = 550
    elif segment_id == 72887:
        columns = ['vol_straight', 'vol_left']
        weights = {'vol_straight': 0.70, 'vol_left': 0.30}
        v_max_peak = 450
        
        # Bổ khuyết làn rẽ phải phụ có lưu lượng thấp (low baseline demand: 5-15 xe ban ngày, 0-4 xe ban đêm)
        if pd.isna(row['vol_right']) or row['vol_right'] == 0:
            if 6 <= hour <= 22:
                row['vol_right'] = float(np.random.randint(5, 16))
            else:
                row['vol_right'] = float(np.random.randint(0, 5))
    elif segment_id == 83624:
        columns = ['vol_straight', 'vol_left']
        weights = {'vol_straight': 0.65, 'vol_left': 0.35}
        v_max_peak = 350
        
        # Bổ khuyết làn rẽ phải phụ có lưu lượng thấp (low baseline demand: 5-15 xe ban ngày, 0-4 xe ban đêm)
        if pd.isna(row['vol_right']) or row['vol_right'] == 0:
            if 6 <= hour <= 22:
                row['vol_right'] = float(np.random.randint(5, 16))
            else:
                row['vol_right'] = float(np.random.randint(0, 5))
    else:
        columns = ['vol_straight', 'vol_left', 'vol_right']
        weights = {'vol_straight': 0.60, 'vol_left': 0.23, 'vol_right': 0.17}
        v_max_peak = 550

    # 1. Xác định các ô bị thiếu hoặc bằng 0
    missing_cols = []
    fixed_cols = []
    
    for col in columns:
        val = row[col]
        if pd.isna(val) or val == 0:
            missing_cols.append(col)
        else:
            fixed_cols.append(col)
            
    # Nếu không còn ô nào khuyết thiếu, kết thúc
    if not missing_cols:
        return row
        
    # Tính tổng lưu lượng có sẵn
    s_fixed = sum(row[col] for col in fixed_cols)
    
    # 2. Sinh ngẫu nhiên tổng lưu lượng mục tiêu V_total cho phân đoạn này theo giờ
    v_target = v_max_peak * factor
    v_min = max(10, int(v_target * 0.9))
    v_max = max(15, int(v_target * 1.1))
    
    v_total = np.random.randint(v_min, v_max + 1)
    # Đảm bảo tổng mục tiêu tối thiểu bằng lượng xe thực tế đang có
    v_total = max(v_total, s_fixed)
    
    # Lượng xe dư cần phân bổ
    r = v_total - s_fixed
    
    if r == 0 or not missing_cols:
        for col in missing_cols:
            row[col] = 0
        return row
        
    # 3. Phân bổ lưu lượng R vào các làn bị khuyết theo tỷ lệ hình học
    base_weights = {col: weights[col] for col in missing_cols}
    
    # Áp dụng nhiễu ngẫu nhiên hành vi lái xe đô thị: +-5% đến +-10%
    noisy_weights = {}
    for col in missing_cols:
        sign = 1 if np.random.rand() > 0.5 else -1
        noise_magnitude = np.random.uniform(0.05, 0.10)
        noise = sign * noise_magnitude
        noisy_weights[col] = base_weights[col] * (1.0 + noise)
        
    # Chuẩn hóa lại các trọng số có nhiễu để tổng bằng 1.0
    sum_noisy = sum(noisy_weights.values())
    norm_weights = {col: w / sum_noisy for col, w in noisy_weights.items()}
    
    # Tính lượng phân bổ làm tròn thành số nguyên không âm
    imputed_vals = {}
    for col in missing_cols:
        imputed_vals[col] = max(0, int(round(r * norm_weights[col])))
        
    # Bù trừ sai số làm tròn để đảm bảo tổng dòng đúng bằng v_total
    current_sum = s_fixed + sum(imputed_vals.values())
    diff = v_total - current_sum
    
    if diff != 0 and missing_cols:
        highest_weight_col = max(missing_cols, key=lambda c: weights[c])
        imputed_vals[highest_weight_col] = max(0, imputed_vals[highest_weight_col] + diff)
        
    # Cập nhật giá trị vào dòng
    for col in missing_cols:
        row[col] = imputed_vals[col]
        
    return row

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
        
    print("[*] Khởi động tiến trình bổ khuyết & làm giàu dữ liệu giao thông hình học đô thị nâng cao...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, "data", "junction_pivot_clean.csv")
    
    if not os.path.exists(csv_path):
        print(f"[!] Lỗi: Không tìm thấy tệp {csv_path}")
        sys.exit(1)
        
    df = pd.read_csv(csv_path)
    print(f" -> Đã nạp {len(df):,} dòng từ {csv_path}")
    
    lanes = ['vol_straight', 'vol_left', 'vol_right']
    
    # Đếm số lượng khuyết thiếu ban đầu
    nan_counts = df[lanes].isna().sum()
    zero_counts = (df[lanes] == 0).sum()
    print("    - Thống kê khuyết thiếu ban đầu:")
    for col in lanes:
        print(f"      * {col}: {nan_counts[col]:,} dòng NaN | {zero_counts[col]:,} dòng bằng 0")
        
    # Chạy bổ khuyết phân nhóm theo SegmentID
    print(" -> Đang bổ khuyết theo đặc thù hình học của từng phân đoạn...")
    
    # Sử dụng numpy array để cập nhật nhanh chóng
    arr_straight = df['vol_straight'].values.copy()
    arr_left = df['vol_left'].values.copy()
    arr_right = df['vol_right'].values.copy()
    arr_seg = df['segment_id'].values
    
    # Trích xuất giờ từ timestamp để sinh lưu lượng nhịp ngày/đêm chân thực
    df_dt = pd.to_datetime(df['timestamp'])
    arr_hour = df_dt.dt.hour.values
    
    imputed_count = 0
    
    for i in range(len(df)):
        seg_id = arr_seg[i]
        hour_val = arr_hour[i]
        row_dict = {
            'vol_straight': arr_straight[i],
            'vol_left': arr_left[i],
            'vol_right': arr_right[i]
        }
        
        # Kiểm tra xem dòng này có chứa NaN hoặc 0 ở các cột tương ứng không
        has_issue = False
        if seg_id == 138:
            has_issue = any(pd.isna(row_dict[c]) or row_dict[c] == 0 for c in ['vol_straight', 'vol_left', 'vol_right'])
        else:
            has_issue = any(pd.isna(row_dict[c]) or row_dict[c] == 0 for c in ['vol_straight', 'vol_left']) or pd.isna(row_dict['vol_right']) or row_dict['vol_right'] == 0
            
        if has_issue:
            imputed_row = impute_row(row_dict, seg_id, hour=hour_val)
            arr_straight[i] = imputed_row['vol_straight']
            arr_left[i] = imputed_row['vol_left']
            arr_right[i] = imputed_row['vol_right']
            imputed_count += 1
            
    # Ghi nhận lại vào DataFrame
    df['vol_straight'] = arr_straight
    df['vol_left'] = arr_left
    df['vol_right'] = arr_right
    
    # Đảm bảo kiểu số nguyên cho các cột lưu lượng
    for col in lanes:
        df[col] = df[col].astype(int)
        
    # Lưu tệp CSV cập nhật
    df.to_csv(csv_path, index=False)
    
    print("\n" + "="*70)
    print(f" [+] TIẾN TRÌNH BỔ KHUYẾT HOÀN THÀNH XUẤT SẮC!")
    print(f"     - Số dòng đã được xử lý bổ khuyết thành công: {imputed_count:,} dòng")
    print(f"     - Trạng thái tệp đã cập nhật: {csv_path}")
    print("     - Thống kê lưu lượng sau làm giàu dữ liệu:")
    print(df[lanes].describe())
    print("="*70)

if __name__ == '__main__':
    main()
