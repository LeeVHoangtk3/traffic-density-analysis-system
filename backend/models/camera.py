from sqlalchemy import Column, Integer, String

from backend.database import Base

class Camera(Base):

    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True)
    camera_id = Column(String, nullable=True)
    name = Column(String)
    location = Column(String)
    baseline_green = Column(Integer, default=30)
    monitored_direction = Column(String, default="inbound")
