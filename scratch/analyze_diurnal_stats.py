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
    df['hour'] = df['timestamp'].dt.hour
    
    print("--- Traffic Volume Statistics by Hour and Segment ---")
    for seg_id in df['segment_id'].unique():
        sub_df = df[df['segment_id'] == seg_id]
        print(f"\n================ Segment {seg_id} ================")
        
        # Group by hour and calculate mean for each lane
        hourly_stats = sub_df.groupby('hour')[['vol_straight', 'vol_left', 'vol_right']].mean()
        print("Hourly Mean Traffic:")
        print(hourly_stats.round(1))
        
        # Calculate min/max of sum of all lanes by hour
        sub_df = sub_df.copy()
        sub_df['total_vol'] = sub_df['vol_straight'] + sub_df['vol_left'] + sub_df['vol_right']
        total_stats = sub_df.groupby('hour')['total_vol'].agg(['min', 'mean', 'max'])
        print("\nHourly Total Volume (Sum of all lanes) Stats:")
        print(total_stats.round(1))

if __name__ == '__main__':
    main()
