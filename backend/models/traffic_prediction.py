from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from backend.database import Base

class TrafficPrediction(Base):

    __tablename__ = "traffic_predictions"

    id = Column(Integer, primary_key=True)
    camera_id = Column(String, nullable=True)
    predicted_density = Column(Float)
    horizon_minutes = Column(Integer, default=15)
    source = Column(String, default="fallback")
    timestamp = Column(DateTime, default=datetime.utcnow)
