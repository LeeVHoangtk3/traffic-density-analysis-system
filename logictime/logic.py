import pandas as pd
import os

base_dir = os.path.dirname(__file__)
file_path = os.path.join(base_dir, '../ml_service/data/urban_traffic.csv')

df = pd.read_csv(file_path)


time = 45
avg = df['Target_Vehicle_Count'].mean()

print(avg)

df['time-green-light'] = 45

for i in range(len(df)):
    t = df.iloc[i]['time-green-light']

    delta = (abs(df.iloc[i]['Target_Vehicle_Count'] - avg) / avg) * 100
    t = t + (delta // 10) * 5

    if df.iloc[i]['Peak_Off_Peak'] == "Peak":
        t += 10
    df.at[i, 'time-green-light'] = t

print(df[['Target_Vehicle_Count', 'Peak_Off_Peak', 'time-green-light']].head())
df.to_csv(file_path, index=False)