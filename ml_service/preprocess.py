import os
import sys
import pandas as pd
import numpy as np

def main():
    # Cấu hình stdout/stderr sang UTF-8 để hiển thị tiếng Việt trên Windows
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
        
    print("[*] Khởi động pipeline tiền xử lý đa nút giao thực tế...")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_csv = os.path.join(base_dir, "data", "ml", "Automated_Traffic_Volume_Counts_20260521.csv")
    out_dir = os.path.join(base_dir, "ml_service", "data")
    
    print(f" -> Nguồn dữ liệu thô: {raw_csv}")
    
    if not os.path.exists(raw_csv):
        print(f"[!] Lỗi: Không tìm thấy tệp {raw_csv}")
        sys.exit(1)
        
    # 1. Đọc tệp dữ liệu lớn một cách hiệu quả
    print(" -> [1/4] Đang đọc các cột cần thiết từ CSV...")
    cols_to_use = ['Yr', 'M', 'D', 'HH', 'MM', 'Vol', 'SegmentID', 'Direction']
    df = pd.read_csv(raw_csv, usecols=cols_to_use)
    print(f"    Tổng số dòng thô đã đọc: {len(df):,}")
    
    # 2. Chuẩn hóa Vol và loại bỏ giá trị âm/lỗi
    print(" -> [2/4] Đang làm sạch cột Vol và các giá trị lỗi...")
    df['Vol_clean'] = df['Vol'].astype(str).str.replace(',', '')
    df['Vol_clean'] = pd.to_numeric(df['Vol_clean'], errors='coerce')
    
    # Lọc bỏ giá trị thiếu và giá trị âm (Vol < 0)
    df = df.dropna(subset=['Vol_clean'])
    df = df[df['Vol_clean'] >= 0]
    df['Vol_clean'] = df['Vol_clean'].astype(int)
    print(f"    Số dòng sau khi làm sạch Vol: {len(df):,}")
    
    # 3. Chuẩn hóa mốc thời gian và làm tròn phút lệch về bin 15 phút
    print(" -> [3/4] Đang chuẩn hóa thời gian và đưa về bin 15 phút chuẩn...")
    datetime_str = (
        df['Yr'].astype(str) + '-' +
        df['M'].astype(str).str.zfill(2) + '-' +
        df['D'].astype(str).str.zfill(2) + ' ' +
        df['HH'].astype(str).str.zfill(2) + ':' +
        df['MM'].astype(str).str.zfill(2)
    )
    df['timestamp'] = pd.to_datetime(datetime_str, errors='coerce')
    df = df.dropna(subset=['timestamp'])
    
    # Làm tròn về bin 15 phút chuẩn (00/15/30/45)
    df['timestamp'] = df['timestamp'].dt.round('15min')
    
    # 4. Gộp trùng lặp logic theo SegmentID, Direction, timestamp bằng mean
    print(" -> [4/4] Đang giải quyết trùng lặp logic...")
    df_clean = (
        df.groupby(['SegmentID', 'Direction', 'timestamp'])['Vol_clean']
        .mean()
        .reset_index()
    )
    df_clean['Vol_clean'] = df_clean['Vol_clean'].round().astype(int)
    print(f"    Số dòng sau khi gộp trùng lặp: {len(df_clean):,}")
    
    # Cấu hình các SegmentID và cách đổi tên cột hướng đi về 3 làn chuẩn
    segments_config = {
        138: {
            'mapping': {'NB': 'vol_straight', 'WB': 'vol_left', 'EB': 'vol_right'},
            'desc': 'Nút giao ngã ba tách làn (SegmentID 138)'
        },
        72887: {
            'mapping': {'EB': 'vol_straight', 'WB': 'vol_left'},
            'desc': 'Tuyến trục Đông-Tây lớn (SegmentID 72887)'
        },
        83624: {
            'mapping': {'NB': 'vol_straight', 'SB': 'vol_left'},
            'desc': 'Tuyến song hành Nam-Bắc (SegmentID 83624)'
        }
    }
    
    target_cols = ['timestamp', 'segment_id', 'vol_straight', 'vol_left', 'vol_right']
    all_segments_chunks = []
    
    # Thực hiện xử lý cho từng Segment
    for seg_id, config in segments_config.items():
        print(f"\n" + "="*70)
        print(f" ĐANG XỬ LÝ SEGMENTID {seg_id} | {config['desc']}")
        print("="*70)
        
        df_seg = df_clean[df_clean['SegmentID'] == seg_id].copy()
        if df_seg.empty:
            print(f"    [!] Cảnh báo: Không tìm thấy dữ liệu cho SegmentID {seg_id}")
            continue
            
        # Thuật toán phát hiện chu kỳ đo lường liên tục tự động
        # Tìm tất cả timestamps duy nhất trong segment và sắp xếp tăng dần
        unique_timestamps = sorted(df_seg['timestamp'].unique())
        ts_series = pd.Series(unique_timestamps)
        
        # Tính khoảng thời gian chênh lệch giữa các mốc liên tiếp
        diffs = ts_series.diff()
        
        # Nếu khoảng chênh lệch > 24 giờ, đánh dấu mốc bắt đầu chu kỳ đo mới (block mới)
        gap_threshold = pd.Timedelta(hours=24)
        block_idx = (diffs > gap_threshold).cumsum()
        
        # Tạo ánh xạ mốc thời gian -> block_id
        ts_to_block = dict(zip(unique_timestamps, block_idx))
        df_seg['block_id'] = df_seg['timestamp'].map(ts_to_block)
        
        print(f"    -> Tự động phát hiện được {block_idx.max() + 1} chu kỳ đo lường liên tục.")
        
        chunks = []
        # Xử lý chi tiết cho từng chu kỳ đo lường
        for block_id, block_df in df_seg.groupby('block_id'):
            block_start = block_df['timestamp'].min()
            block_end = block_df['timestamp'].max()
            
            # Xoay trục cột Direction thành các cột hướng rẽ
            p_pivot = block_df.pivot(index='timestamp', columns='Direction', values='Vol_clean').reset_index()
            
            # Áp dụng ánh xạ đổi tên cột hướng đi tương ứng
            p_pivot = p_pivot.rename(columns=config['mapping'])
            
            # Đảm bảo tất cả các cột hướng cần thiết đều tồn tại trong dataframe
            p_pivot['segment_id'] = seg_id
            for col in target_cols:
                if col not in p_pivot.columns:
                    p_pivot[col] = np.nan
            
            p_pivot = p_pivot[target_cols]
            
            # Đảm bảo kiểu số thực để nội suy mượt mà
            for col in ['vol_straight', 'vol_left', 'vol_right']:
                p_pivot[col] = p_pivot[col].astype(float)
                
            # Thiết lập index và resample về chuỗi thời gian liên tục 15 phút cho chu kỳ này
            p_pivot = p_pivot.set_index('timestamp').sort_index()
            # resample bằng cách nội suy thời gian, giữ segment_id ổn định
            p_pivot_res = p_pivot[['vol_straight', 'vol_left', 'vol_right']].resample('15min').asfreq()
            p_pivot_res = p_pivot_res.interpolate(method='time').ffill().bfill()
            p_pivot_res['segment_id'] = seg_id
            
            # Lọc bỏ các block quá ngắn (ít hơn 3 giờ = 12 dòng) để tránh nhiễu
            if len(p_pivot_res) >= 12:
                chunks.append(p_pivot_res.reset_index())
                
        if not chunks:
            print(f"    [!] Cảnh báo: Không có chu kỳ đo nào đủ điều kiện cho SegmentID {seg_id}")
            continue
            
        # Gộp tất cả các chu kỳ đo của Segment lại
        df_seg_final = pd.concat(chunks, ignore_index=True)
        df_seg_final = df_seg_final.sort_values('timestamp').reset_index(drop=True)
        all_segments_chunks.append(df_seg_final)
        
        print(f"    [+] Tiền xử lý xong Segment {seg_id}: {len(df_seg_final):,} dòng")
        
    if all_segments_chunks:
        # Gộp tất cả các Segment thành 1 file duy nhất
        df_merged = pd.concat(all_segments_chunks, ignore_index=True)
        df_merged = df_merged.sort_values(['timestamp', 'segment_id']).reset_index(drop=True)
        
        # Sắp xếp các cột cho đẹp mắt
        df_merged = df_merged[target_cols]
        
        # Lưu trữ tệp dữ liệu sạch hợp nhất
        out_csv = os.path.join(out_dir, "junction_pivot_clean.csv")
        os.makedirs(out_dir, exist_ok=True)
        df_merged.to_csv(out_csv, index=False)
        
        print("\n" + "="*70)
        print(f" [+] ĐÃ GỘP THÀNH CÔNG TỆP HỢP NHẤT: {out_csv}")
        print(f"     Tổng số dòng sau khi hợp nhất 3 nút giao: {len(df_merged):,}")
        print("     Thống kê lưu lượng 3 làn đường chuẩn:")
        print(df_merged[['vol_straight', 'vol_left', 'vol_right']].describe())
        print("="*70)
    else:
        print("[!] Lỗi: Không có dữ liệu sạch nào được tạo ra.")
        
    print("\n" + "="*70)
    print("[+] PIPELINE TIỀN XỬ LÝ ĐA NÚT GIAO ĐÃ HOÀN THÀNH XUẤT SẮC!")
    print("="*70)

if __name__ == '__main__':
    main()
