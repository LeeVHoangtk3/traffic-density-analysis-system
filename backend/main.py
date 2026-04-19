from fastapi import FastAPI

from backend.api import aggregation_routes
from backend.api import camera_routes
from backend.api import detection_routes
from backend.api import health_routes
from backend.api import prediction_routes
from backend.api import traffic_routes
from backend.config import settings
from backend.database import Base, engine, sync_vehicle_detection_schema
from backend.models import Camera, TrafficAggregation, TrafficPrediction, VehicleDetection

app = FastAPI(title=settings.api_title)

Base.metadata.create_all(bind=engine)
sync_vehicle_detection_schema()

app.include_router(detection_routes.router)
app.include_router(traffic_routes.router)
app.include_router(aggregation_routes.router)
app.include_router(prediction_routes.router)
app.include_router(camera_routes.router)
app.include_router(health_routes.router)
