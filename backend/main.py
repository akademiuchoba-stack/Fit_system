import os
import logging
from pathlib import Path
from time import time
from typing import Any, Dict, Optional, List

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from . import models, database, logic

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("fit_backend")

app = FastAPI(title="Fit_system API", version="3.1.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

INDEX_FILE = FRONTEND_DIR / "index.html"
INDEX_JS_FILE = FRONTEND_DIR / "index.js"
ADMIN_FILE = FRONTEND_DIR / "admin.html"
ADMIN_JS_FILE = FRONTEND_DIR / "admin.js"
BUILDER_FILE = FRONTEND_DIR / "builder.html"
BUILDER_JS_FILE = FRONTEND_DIR / "builder.js"

models.Base.metadata.create_all(bind=database.engine)

# ---- Static frontend ----
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_index():
    return FileResponse(str(INDEX_FILE))


@app.get("/admin")
def serve_admin():
    return FileResponse(str(ADMIN_FILE))


@app.get("/builder")
def serve_builder():
    return FileResponse(str(BUILDER_FILE))


# -----------------------------
# Helpers: cache garments list
# -----------------------------
_cache_items: Optional[List[models.Garment]] = None
_cache_ts: float = 0.0
CACHE_TTL = 10.0  # seconds


def get_cached_items(db: Session) -> List[models.Garment]:
    global _cache_items, _cache_ts
    now = time()
    if _cache_items is not None and (now - _cache_ts) < CACHE_TTL:
        return _cache_items
    items = db.query(models.Garment).order_by(models.Garment.id.desc()).all()
    _cache_items = items
    _cache_ts = now
    return items


# -----------------------------
# API: garments
# -----------------------------
@app.get("/api/garments")
def list_garments(db: Session = Depends(database.get_db)):
    items = get_cached_items(db)
    out = []
    for g in items:
        d = {c.name: getattr(g, c.name) for c in g.__table__.columns}
        out.append(d)
    return out


@app.get("/api/garments/{garment_id}")
def get_garment(garment_id: int, db: Session = Depends(database.get_db)):
    g = db.query(models.Garment).filter(models.Garment.id == garment_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Garment not found")
    d = {c.name: getattr(g, c.name) for c in g.__table__.columns}
    return d


@app.delete("/api/garments/{garment_id}")
def delete_garment(garment_id: int, db: Session = Depends(database.get_db)):
    g = db.query(models.Garment).filter(models.Garment.id == garment_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Garment not found")
    db.delete(g)
    db.commit()

    global _cache_items, _cache_ts
    _cache_items = None
    _cache_ts = 0.0

    return {"ok": True}


@app.post("/api/garments")
def upsert_garment(payload: Dict[str, Any] = Body(...), db: Session = Depends(database.get_db)):
    sku = (payload.get("sku") or "").strip()
    if not sku:
        raise HTTPException(status_code=400, detail="sku обязателен")

    g = db.query(models.Garment).filter(models.Garment.sku == sku).first()
    if not g:
        g = models.Garment(sku=sku)

    for k in ["name", "platform", "image_url", "image_url_back", "price", "in_stock"]:
        if k in payload:
            setattr(g, k, payload.get(k))

    if "metrics" in payload:
        g.metrics = payload.get("metrics")
        flag_modified(g, "metrics")

    db.add(g)
    db.commit()
    db.refresh(g)

    global _cache_items, _cache_ts
    _cache_items = None
    _cache_ts = 0.0

    return {"ok": True, "id": g.id}


@app.post("/api/garments/{garment_id}/metrics")
def save_garment_metrics(garment_id: int, payload: Dict[str, Any] = Body(...), db: Session = Depends(database.get_db)):
    g = db.query(models.Garment).filter(models.Garment.id == garment_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Garment not found")

    metrics = g.metrics or {}
    metrics["v31"] = payload
    g.metrics = metrics
    flag_modified(g, "metrics")

    db.add(g)
    db.commit()
    db.refresh(g)

    global _cache_items, _cache_ts
    _cache_items = None
    _cache_ts = 0.0

    return {"ok": True}


# -----------------------------
# API: profiles
# -----------------------------
@app.get("/api/profiles")
def list_profiles(db: Session = Depends(database.get_db)):
    items = db.query(models.BodyProfile).order_by(models.BodyProfile.id.desc()).all()
    out = []
    for p in items:
        d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
        out.append(d)
    return out


@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: int, db: Session = Depends(database.get_db)):
    p = db.query(models.BodyProfile).filter(models.BodyProfile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
    return d


@app.post("/api/profiles")
def create_profile(payload: models.BodyProfileCreate, db: Session = Depends(database.get_db)):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name обязателен")

    if db.query(models.BodyProfile).filter(models.BodyProfile.name == name).first():
        raise HTTPException(status_code=400, detail="Profile name already exists")

    # Pydantic v2: model_dump() вместо dict()
    p = models.BodyProfile(**payload.model_dump())
    p.name = name
    if not p.gender:
        p.gender = "male"
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"ok": True, "id": p.id}


@app.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: int, db: Session = Depends(database.get_db)):
    p = db.query(models.BodyProfile).filter(models.BodyProfile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    db.delete(p)
    db.commit()
    return {"ok": True}


# -----------------------------
# API: calculate fit
# -----------------------------
@app.post("/api/calculate")
def calculate(req: models.CalculateRequest, db: Session = Depends(database.get_db)):
    profile = db.query(models.BodyProfile).filter(models.BodyProfile.id == req.profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # ВАЖНО ДЛЯ АЛГОРИТМА:
    # Движок (logic.py) работает по зонам: sleeve, outseam и т.д.
    # Поэтому тут мы приводим поля профиля к КЛЮЧАМ движка:
    # - sleeve <- arm_length
    # - outseam <- leg_length
    buyer = {
        "gender": (profile.gender or "male").lower(),
        "measurements": {
            # full circumferences
            "chest": getattr(profile, "chest", None),
            "waist_top": getattr(profile, "waist_top", None),
            "belly": getattr(profile, "belly", None),
            "hips": getattr(profile, "hips", None),
            "waist_bottom": getattr(profile, "waist_bottom", None),
            "high_hip": getattr(profile, "high_hip", None),
            "thigh": getattr(profile, "thigh", None),
            "bicep": getattr(profile, "bicep", None),
            # lengths
            "shoulders": getattr(profile, "shoulders", None),
            "sleeve": getattr(profile, "arm_length", None),
            "inseam": getattr(profile, "inseam", None),
            "outseam": getattr(profile, "leg_length", None),
            "length_top": None,
        },
        "problem_zones": getattr(profile, "problem_zones", []) or [],
        "comfort_C": getattr(profile, "comfort_C", {}) or {},
    }

    items = get_cached_items(db)
    results: List[Dict[str, Any]] = []

    for item in items:
        metrics = item.metrics or {}
        v31 = metrics.get("v31") if isinstance(metrics, dict) else None
        if not v31:
            continue

        try:
            fit = logic.calculate_fit_v31(buyer, v31)
        except Exception as e:
            logger.warning("calculate_fit_v31 failed for garment id=%s: %s", item.id, e)
            continue

        results.append({
            "garment_id": item.id,
            "sku": item.sku,
            "name": item.name,
            "platform": item.platform,
            "image_url": item.image_url,
            "image_url_back": item.image_url_back,
            "price": item.price,
            "in_stock": item.in_stock,
            "fit": fit,
        })

    return {"ok": True, "results": results}


# -----------------------------
# API: feedback (learning / calibration)
# -----------------------------
@app.post("/api/feedback")
def submit_feedback(payload: models.FeedbackSubmit, db: Session = Depends(database.get_db)):
    g = db.query(models.Garment).filter(models.Garment.id == payload.garment_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Garment not found")

    p = db.query(models.BodyProfile).filter(models.BodyProfile.id == payload.user_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")

    fb = models.Feedback(
        garment_id=payload.garment_id,
        user_id=payload.user_id,
        size_selected=payload.size_selected,
        fit_rating=payload.fit_rating,
        notes=payload.notes,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return {"ok": True, "id": fb.id}


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)