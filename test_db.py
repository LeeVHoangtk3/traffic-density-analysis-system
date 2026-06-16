from pymongo import MongoClient
import json
client = MongoClient('mongodb://localhost:27017/')
db = client['traffic_db']
rows = list(db.traffic_aggregation.find().sort("timestamp", -1).limit(5))
for r in rows:
    print(r.get("camera_id"), r.get("timestamp"), r.get("vehicle_count"))
