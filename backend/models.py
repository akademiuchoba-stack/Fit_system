from sqlalchemy import Column, Integer, String, Float, JSON, Boolean, ForeignKey, DateTime
from datetime import datetime, timezone
from .database import Base
from pydantic import BaseModel
from typing import Dict, Optional, Any, List

def utc_now():
    return datetime.now(timezone.utc)

# ============================
#   SQLAlchemy MODELS
# ============================

class Garment(Base):
    __tablename__ = "garments"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    name = Column(String)
    platform = Column(String) 
    image_url = Column(String, nullable=True)       
    image_url_back = Column(String, nullable=True)  
    price = Column(Float, nullable=True)
    in_stock = Column(Boolean, default=True)
    metrics = Column(JSON)

class Prior(Base):
    __tablename__ = "priors"

    id = Column(Integer, primary_key=True, index=True)
    garment_id = Column(Integer, ForeignKey("garments.id"))
    size_label = Column(String)
    mu_chest = Column(Float)
    sigma_chest = Column(Float, default=1.0)
    mu_sleeve = Column(Float)
    sigma_sleeve = Column(Float, default=1.0)

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    garment_id = Column(Integer, ForeignKey("garments.id"))
    user_id = Column(String)
    size_selected = Column(String) 
    is_point_zero = Column(Boolean, default=False) 
    fit_matrix = Column(JSON, nullable=True) 
    created_at = Column(DateTime(timezone=True), default=utc_now)

class BodyProfile(Base):
    __tablename__ = "body_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    gender = Column(String)
    height = Column(Float)
    
    # --- ЕДИНАЯ МАТРИЦА ЗАМЕРОВ (ТЕЛО) ---
    shoulders = Column(Float, nullable=True)
    back_width = Column(Float, nullable=True)
    chest = Column(Float, nullable=True)
    underbust = Column(Float, nullable=True)     # Под грудью (жен)
    waist_top = Column(Float, nullable=True)     # Естественная талия
    belly = Column(Float, nullable=True)         # Живот (выступающая часть)
    waist_bottom = Column(Float, nullable=True)  # Пояс брюк (ремень)
    high_hip = Column(Float, nullable=True)      # Косточки таза
    hips = Column(Float, nullable=True)
    thigh = Column(Float, nullable=True)
    knee = Column(Float, nullable=True)
    calf = Column(Float, nullable=True)
    bicep = Column(Float, nullable=True)
    neck = Column(Float, nullable=True)
    
    arm_length = Column(Float, nullable=True)
    leg_length = Column(Float, nullable=True)    # outseam
    inseam = Column(Float, nullable=True)
    length_dress = Column(Float, nullable=True)  # Длина для платьев
    
    # --- НАСТРОЙКИ IP 2.0 ---
    problem_zones = Column(JSON, nullable=True) 
    comfort_C = Column(JSON, nullable=True)     

    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

# ============================
#   Pydantic SCHEMAS
# ============================

class BodyProfileCreate(BaseModel):
    name: str
    gender: str = "male"
    height: float
    shoulders: Optional[float] = None
    back_width: Optional[float] = None
    chest: Optional[float] = None
    underbust: Optional[float] = None
    waist_top: Optional[float] = None
    belly: Optional[float] = None
    waist_bottom: Optional[float] = None
    high_hip: Optional[float] = None
    hips: Optional[float] = None
    thigh: Optional[float] = None
    knee: Optional[float] = None
    calf: Optional[float] = None
    bicep: Optional[float] = None
    neck: Optional[float] = None
    arm_length: Optional[float] = None
    leg_length: Optional[float] = None
    inseam: Optional[float] = None
    length_dress: Optional[float] = None
    
    problem_zones: Optional[List[str]] = None
    comfort_C: Optional[Dict[str, Any]] = None

class CalculateRequest(BaseModel):
    profile_id: int

class FeedbackSubmit(BaseModel):
    garment_id: int
    user_id: str
    size_selected: str
    is_point_zero: bool = False
    fit_matrix: Optional[Dict[str, str]] = None