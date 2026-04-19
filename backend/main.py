import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.api import aggregation_routes
from backend.api import camera_routes
from backend.api import detection_routes
from backend.api import health_routes
from backend.api import prediction_routes
from backend.api import traffic_routes
from backend.config import settings
from backend.database import Base, engine, sync_vehicle_detection_schema
from backend.models import Camera, TrafficAggregation, TrafficPrediction, VehicleDetection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI(title=settings.api_title)

Base.metadata.create_all(bind=engine)
sync_vehicle_detection_schema()

app.include_router(detection_routes.router)
app.include_router(traffic_routes.router)
app.include_router(aggregation_routes.router)
app.include_router(prediction_routes.router)
app.include_router(camera_routes.router)
app.include_router(health_routes.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started_at = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "%s %s -> %s (%sms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "path": request.url.path,
        },
    )
