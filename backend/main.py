from fastapi import FastAPI
from backend.database import engine, Base, sync_vehicle_detection_schema

from backend.models.camera import Camera
from backend.models.vehicle_detection import VehicleDetection
from backend.models.traffic_aggregation import TrafficAggregation
from backend.models.traffic_prediction import TrafficPrediction

from backend.api import detection_routes
from backend.api import traffic_routes
from backend.api import aggregation_routes
from backend.api import prediction_routes
# ===== ADD THIS =====
from backend.api import video


app = FastAPI(title="Traffic AI Backend")

Base.metadata.create_all(bind=engine)
sync_vehicle_detection_schema()

app.include_router(video.router)
app.include_router(detection_routes.router)
app.include_router(traffic_routes.router)
app.include_router(aggregation_routes.router)
app.include_router(prediction_routes.router)
