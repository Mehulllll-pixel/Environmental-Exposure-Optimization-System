from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from .database import Base

class ExposureLog(Base):
    __tablename__ = "exposure_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String)
    date = Column(String)
    station = Column(String)
    duration = Column(Integer)
    pevi_score = Column(Float)
    risk_level = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())