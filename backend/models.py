
from sqlalchemy import Column, Integer, String, Float, JSON, Boolean, ForeignKey
from .database import Base
from pydantic import BaseModel
from typing import Dict, Optional, List

# --- SQLAlchemy Models ---

class Garment(Base):
    __tablename__ = "garments"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    name = Column(String)
    platform = Column(String) # 'ostin' or 'lamoda'
    image_url = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    in_stock = Column(Boolean, default=True)
    # metrics хранит JSON вида {"S": {"chest": 52, "shoulder": 44, "length": 70, "sleeve": 62}, ...}
    metrics = Column(JSON) 

class Prior(Base):
    """Таблица для хранения параметров распределения размеров (для калибровки)"""
    __tablename__ = "priors"

    id = Column(Integer, primary_key=True, index=True)
    garment_id = Column(Integer, ForeignKey("garments.id"))
    size_label = Column(String) # e.g., 'M'
    mu_chest = Column(Float)
    sigma_chest = Column(Float, default=1.0)
    mu_sleeve = Column(Float)
    sigma_sleeve = Column(Float, default=1.0)

class Feedback(Base):
    """Таблица отзывов пользователей для обучения системы"""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    garment_id = Column(Integer, ForeignKey("garments.id"))
    user_id = Column(String)
    size_selected = Column(String)
    # user_judgment: 1 (Too small), 0 (Good), -1 (Too big)
    judgment = Column(Integer) 
    real_measurements = Column(JSON) # Снятые замеры вещи пользователем

# --- Pydantic Schemas ---

class UserMetrics(BaseModel):
    name: str
    gender: str
    height: float
    chest: float
    shoulders: float
    waist: float
    hips: float
    arm_length: float
    leg_length: float

class FitRequest(BaseModel):
    user: UserMetrics
    sku: Optional[str] = None

class FeedbackSubmit(BaseModel):
    garment_id: int
    user_id: str
    size_selected: str
    judgment: int
    real_measurements: Optional[Dict[str, float]] = None
