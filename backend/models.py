from __future__ import annotations

from typing import Optional, List, Dict, Any

from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.types import JSON
from pydantic import BaseModel, Field

from .database import Base


# -----------------------------
# SQLAlchemy ORM models
# -----------------------------

class Garment(Base):
    __tablename__ = "garments"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True, nullable=False)

    name = Column(String, nullable=True)
    platform = Column(String, nullable=True)

    image_url = Column(String, nullable=True)
    image_url_back = Column(String, nullable=True)

    price = Column(Float, nullable=True)
    in_stock = Column(Boolean, default=True)

    # unified storage for v3.1 format:
    # metrics: { schema_version:"v3.1", v31:{...} }
    metrics = Column(JSON, nullable=True)


class BodyProfile(Base):
    __tablename__ = "body_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

    # only male/female for now
    gender = Column(String, default="male")

    # optional, not required for MVP but kept
    height = Column(Float, nullable=True)

    # FULL circumferences (cm around body)
    chest = Column(Float, nullable=True)
    waist_top = Column(Float, nullable=True)
    belly = Column(Float, nullable=True)
    hips = Column(Float, nullable=True)

    waist_bottom = Column(Float, nullable=True)   # belt/waist where trousers sit
    high_hip = Column(Float, nullable=True)
    thigh = Column(Float, nullable=True)
    bicep = Column(Float, nullable=True)

    # lengths (cm)
    shoulders = Column(Float, nullable=True)      # shoulder width/length (as used in engine)
    arm_length = Column(Float, nullable=True)     # sleeve/arm length
    inseam = Column(Float, nullable=True)         # inseam length
    leg_length = Column(Float, nullable=True)     # outseam/leg length

    # problem zones flags, e.g. ["belly","sleeve","waist_bottom"]
    problem_zones = Column(JSON, nullable=True)

    # comfort / personal preferences per zone (reserved for later)
    comfort_C = Column(JSON, nullable=True)


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)

    garment_id = Column(Integer, index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=False)  # profile_id

    size_selected = Column(String, nullable=True)
    is_point_zero = Column(Boolean, default=False)

    # we store v3.1 payload snapshot (fit matrix / v31 etc.)
    fit_matrix = Column(JSON, nullable=True)


# -----------------------------
# Pydantic request/response models
# -----------------------------

class BodyProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    gender: str = Field(default="male")

    height: Optional[float] = None

    chest: Optional[float] = None
    waist_top: Optional[float] = None
    belly: Optional[float] = None
    hips: Optional[float] = None

    waist_bottom: Optional[float] = None
    high_hip: Optional[float] = None
    thigh: Optional[float] = None
    bicep: Optional[float] = None

    shoulders: Optional[float] = None
    arm_length: Optional[float] = None
    inseam: Optional[float] = None
    leg_length: Optional[float] = None

    problem_zones: Optional[List[str]] = None
    comfort_C: Optional[Dict[str, Any]] = None


class CalculateRequest(BaseModel):
    profile_id: int


class FeedbackSubmit(BaseModel):
    garment_id: int
    user_id: int  # profile_id
    size_selected: Optional[str] = None
    is_point_zero: bool = False
    fit_matrix: Optional[Dict[str, Any]] = None