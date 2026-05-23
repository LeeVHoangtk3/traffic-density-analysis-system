import os
import sys
import pandas as pd
import numpy as np

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
    
    print("--- Checking for consecutive zeros in all segments and lanes ---")
    for seg_id in df['segment_id'].unique():
        sub_df = df[df['segment_id'] == seg_id].copy()
        print(f"\nSegment {seg_id} (Total rows: {len(sub_df)}):")
        
        for col in lanes:
            # Mask of zeros
            is_zero = (sub_df[col] == 0)
            
            # Identify groups of consecutive values
            group_ids = (is_zero != is_zero.shift()).cumsum()
            
            # Filter groups that are zero and get their sizes
            zero_groups = group_ids[is_zero]
            if zero_groups.empty:
                print(f"  * {col}: No zeros found.")
                continue
                
            group_sizes = zero_groups.value_counts().sort_index()
            
            # Find groups with size >= 4 (>= 1 hour)
            long_zero_groups = group_sizes[group_sizes >= 4]
            
            total_zeros = is_zero.sum()
            print(f"  * {col}: Total 0s = {total_zeros} ({total_zeros/len(sub_df)*100:.2f}%)")
            if not long_zero_groups.empty:
                print(f"    Found {len(long_zero_groups)} streaks of consecutive 0s lasting >= 1 hour:")
                for grp_id, size in long_zero_groups.items():
                    streak_rows = sub_df[group_ids == grp_id]
                    start_t = streak_rows['timestamp'].min()
                    end_t = streak_rows['timestamp'].max()
                    hours = size * 15 / 60
                    print(f"      - {start_t} to {end_t} | Duration: {hours} hours ({size} consecutive 15-min intervals)")
            else:
                print("    No streaks of consecutive 0s lasting >= 1 hour.")

if __name__ == '__main__':
    main()
