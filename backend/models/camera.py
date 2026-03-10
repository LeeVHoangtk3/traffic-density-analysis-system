from sqlalchemy import Column, Integer, String
from backend.database import Base

class Camera(Base):

    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    location = Column(String)