from sqlalchemy import Column, Integer, Float, DateTime
from datetime import datetime
from backend.database import Base

class TrafficPrediction(Base):

    __tablename__ = "traffic_predictions"

    id = Column(Integer, primary_key=True)
    predicted_density = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)