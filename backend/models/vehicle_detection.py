from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Index, Integer, String

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

    __table_args__ = (
        Index("ix_vehicle_detections_event_id", "event_id"),
        Index("ix_vehicle_detections_camera_id", "camera_id"),
        Index("ix_vehicle_detections_timestamp", "timestamp"),
    )
