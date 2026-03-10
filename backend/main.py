from fastapi import FastAPI
from backend.database import engine, Base

from backend.api import detection_routes
from backend.api import traffic_routes
from backend.api import aggregation_routes
from backend.api import prediction_routes

app = FastAPI(title="Traffic AI Backend")

Base.metadata.create_all(bind=engine)

app.include_router(detection_routes.router)
app.include_router(traffic_routes.router)
app.include_router(aggregation_routes.router)
app.include_router(prediction_routes.router)