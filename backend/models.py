
from sqlalchemy import Column, Integer, String, Float, JSON, Boolean, ForeignKey, DateTime
from datetime import datetime
from .database import Base
from pydantic import BaseModel
from typing import Dict, Optional

# ============================
#   SQLAlchemy MODELS
# ============================

class Garment(Base):
    __tablename__ = "garments"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    name = Column(String)
    platform = Column(String)  # 'ostin' or 'lamoda'
    image_url = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    in_stock = Column(Boolean, default=True)

    # Пример структуры:
    # {
    #   "S": {"chest": 52, "shoulder": 44, "length": 70, "sleeve": 62},
    #   "M": {...}
    # }
    metrics = Column(JSON)


class Prior(Base):
    """Параметры распределения размеров для байесовской калибровки."""
    __tablename__ = "priors"

    id = Column(Integer, primary_key=True, index=True)
    garment_id = Column(Integer, ForeignKey("garments.id"))
    size_label = Column(String)  # e.g., "M"

    mu_chest = Column(Float)
    sigma_chest = Column(Float, default=1.0)

    mu_sleeve = Column(Float)
    sigma_sleeve = Column(Float, default=1.0)


class Feedback(Base):
    """Отзывы пользователей для обучения системы."""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    garment_id = Column(Integer, ForeignKey("garments.id"))
    user_id = Column(String)
    size_selected = Column(String)

    # 1 = маловато, 0 = идеально, -1 = велико
    judgment = Column(Integer)

    # Пример: {"chest": 51.5}
    real_measurements = Column(JSON)


class BodyProfile(Base):
    """Профиль тела (сохраняется по уникальному имени)."""
    __tablename__ = "body_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    gender = Column(String, default="male")

    height = Column(Float)
    chest = Column(Float)
    shoulders = Column(Float)
    waist = Column(Float)
    hips = Column(Float)
    arm_length = Column(Float)
    leg_length = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================
#   Pydantic SCHEMAS
# ============================

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


class CalculateRequest(BaseModel):
    """Запрос на рекомендации по активному профилю из 'Кабинета'."""
    profile_id: int



class BodyProfileCreate(BaseModel):
    name: str
    gender: str = "male"
    height: float
    chest: float
    shoulders: float
    waist: float
    hips: float
    arm_length: float
    leg_length: float


class BodyProfileUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    height: Optional[float] = None
    chest: Optional[float] = None
    shoulders: Optional[float] = None
    waist: Optional[float] = None
    hips: Optional[float] = None
    arm_length: Optional[float] = None
    leg_length: Optional[float] = None


class FeedbackSubmit(BaseModel):
    garment_id: int
    user_id: str
    size_selected: str
    judgment: int
    real_measurements: Optional[Dict[str, float]] = None
