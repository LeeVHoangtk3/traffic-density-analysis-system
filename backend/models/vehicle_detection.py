from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from backend.database import Base

class VehicleDetection(Base):

    __tablename__ = "vehicle_detections"

    id = Column(Integer, primary_key=True)
    event_id = Column(String)
    camera_id = Column(String)
    track_id = Column(String)
    vehicle_type = Column(String)
    density = Column(String)
    event_type = Column(String)
    confidence = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
