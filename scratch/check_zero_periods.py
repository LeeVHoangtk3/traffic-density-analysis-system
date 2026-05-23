import os
import sys
import pandas as pd

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    base_dir = r"D:\GIT REPO\trafffic-density-analysis-system\traffic-density-analysis-system"
    csv_path = os.path.join(base_dir, "ml_service", "data", "junction_pivot_clean.csv")
    
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return
        
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(['segment_id', 'timestamp'])
    
    lanes = ['vol_straight', 'vol_left', 'vol_right']
    
    print("--- Detailed check for long periods of consecutive zeros (>= 4 hours) ---")
    
    for seg_id in df['segment_id'].unique():
        sub_df = df[df['segment_id'] == seg_id].copy()
        
        for col in lanes:
            # Mask of zeros
            is_zero = (sub_df[col] == 0)
            group_ids = (is_zero != is_zero.shift()).cumsum()
            zero_groups = group_ids[is_zero]
            
            if zero_groups.empty:
                continue
                
            group_sizes = zero_groups.value_counts().sort_index()
            # Streaks >= 16 intervals (>= 4 hours)
            long_streaks = group_sizes[group_sizes >= 16]
            
            if not long_streaks.empty:
                print(f"\nSegment {seg_id} - Lane '{col}': Found {len(long_streaks)} streaks >= 4 hours:")
                for grp_id, size in long_streaks.items():
                    streak_rows = sub_df[group_ids == grp_id]
                    start_t = streak_rows['timestamp'].min()
                    end_t = streak_rows['timestamp'].max()
                    hours = size * 15 / 60
                    print(f"  * From {start_t} to {end_t} | Duration: {hours:.2f} hours ({size} intervals)")
            else:
                print(f"Segment {seg_id} - Lane '{col}': No streaks >= 4 hours.")

if __name__ == '__main__':
    main()
