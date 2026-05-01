from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from backend.database import Base

class TrafficAggregation(Base):

    __tablename__ = "traffic_aggregation"

    id = Column(Integer, primary_key=True)
    camera_id = Column(String)
    vehicle_count = Column(Integer)
    inbound_count = Column(Integer, default=0)
    queue_proxy = Column(Integer, default=0)
    congestion_level = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
