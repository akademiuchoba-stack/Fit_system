from sqlalchemy import Column, Integer, String, Float, JSON, Boolean, ForeignKey, DateTime
from datetime import datetime
from .database import Base
from pydantic import BaseModel
from typing import Dict, Optional, Any

# ============================
#   SQLAlchemy MODELS
# ============================

class Garment(Base):
    __tablename__ = "garments"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    name = Column(String)
    platform = Column(String)  # 'ostin', 'lamoda' или 'manual'
    image_url = Column(String, nullable=True)       # Вид спереди
    image_url_back = Column(String, nullable=True)  # Вид сзади (НОВОЕ)
    price = Column(Float, nullable=True)
    in_stock = Column(Boolean, default=True)

    # В metrics теперь будет лежать структурированный JSON:
    # {
    #   "theory": {"model_chest": 90, "elastane": 2, "fit_profile": "regular"...},
    #   "ground_truth": {
    #       "L": {"chest": 104, "length": 72, "inseam": 80},
    #       "XL": {"chest": 108, "length": 74, "inseam": 81}
    #   }
    # }
    metrics = Column(JSON)


class Prior(Base):
    """Параметры распределения размеров для байесовской калибровки."""
    __tablename__ = "priors"

    id = Column(Integer, primary_key=True, index=True)
    garment_id = Column(Integer, ForeignKey("garments.id"))
    size_label = Column(String)

    mu_chest = Column(Float)
    sigma_chest = Column(Float, default=1.0)
    mu_sleeve = Column(Float)
    sigma_sleeve = Column(Float, default=1.0)


class Feedback(Base):
    """Матрица примерки (Ground Truth Feedback)"""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    garment_id = Column(Integer, ForeignKey("garments.id"))
    user_id = Column(String)
    
    size_selected = Column(String) # Какой размер меряли (например, XL)
    
    # Главный вердикт: является ли это "Точкой Ноль" (идеальным припуском)
    is_point_zero = Column(Boolean, default=False) 
    
    # Матрица ощущений в формате JSON:
    # {"chest": "жмет", "sleeve": "коротко", "belly": "подскакивает"}
    fit_matrix = Column(JSON, nullable=True) 

    created_at = Column(DateTime, default=datetime.utcnow)


class BodyProfile(Base):
    __tablename__ = "body_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    gender = Column(String)
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

class CalculateRequest(BaseModel):
    profile_id: int

class FeedbackSubmit(BaseModel):
    garment_id: int
    user_id: str
    size_selected: str
    is_point_zero: bool = False
    fit_matrix: Optional[Dict[str, str]] = None
