import os
import sys
import logging
import subprocess
from pathlib import Path
from time import time
from typing import Any, Dict, Optional, List

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect, or_

from . import models, database, logic, calibration

# -----------------------------
# LOGGING
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("fit_backend")

app = FastAPI(title="Fit_system API", version="2.0.0")

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

_ITEMS_CACHE = {"ts": 0.0, "items": None}
CACHE_TTL_SEC = int(os.getenv("FIT_ITEMS_CACHE_TTL", "10"))

def invalidate_items_cache():
    _ITEMS_CACHE["items"] = None
    _ITEMS_CACHE["ts"] = 0.0

def get_cached_items(db: Session):
    now = time()
    if _ITEMS_CACHE["items"] is None or (now - _ITEMS_CACHE["ts"]) > CACHE_TTL_SEC:
        items = db.query(models.Garment).filter(models.Garment.in_stock == True).all()
        _ITEMS_CACHE["items"] = items
        _ITEMS_CACHE["ts"] = now
    return _ITEMS_CACHE["items"]

def _coerce_float(x: Any) -> Optional[float]:
    try:
        if x is None: return None
        s = str(x).strip().replace(",", ".")
        if s == "": return None
        return float(s)
    except Exception:
        return None

def garment_to_dict(g: models.Garment) -> Dict[str, Any]:
    return {
        "id": g.id,
        "sku": g.sku,
        "name": g.name,
        "platform": g.platform,
        "image_url": g.image_url,
        "image_url_back": getattr(g, "image_url_back", None),
        "price": g.price,
        "in_stock": bool(g.in_stock),
        "metrics": g.metrics or {},
    }

@app.post("/api/webhook-deploy")
def webhook_deploy():
    logger.info("Received deploy webhook. Initiating update...")
    try:
        git_pull = subprocess.run(["git", "pull"], cwd=str(BASE_DIR), capture_output=True, text=True, timeout=30)
        if git_pull.returncode != 0:
            raise HTTPException(status_code=500, detail="Git pull failed")
            
        subprocess.run(["sudo", "systemctl", "restart", "fit_system"], capture_output=True, text=True, timeout=10)
        return {"status": "success", "message": "Deployment initiated"}
    except Exception as e:
        logger.exception("Deploy failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/profiles")
def list_profiles(db: Session = Depends(database.get_db)):
    profiles = db.query(models.BodyProfile).order_by(models.BodyProfile.updated_at.desc()).all()
    return [{"id": p.id, "name": p.name, "gender": p.gender, "height": p.height, "chest": p.chest, "shoulders": p.shoulders, "waist": p.waist, "hips": p.hips, "arm_length": p.arm_length, "leg_length": p.leg_length, "inseam": p.inseam} for p in profiles]

@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: int, db: Session = Depends(database.get_db)):
    p = db.query(models.BodyProfile).filter(models.BodyProfile.id == profile_id).first()
    if not p: raise HTTPException(status_code=404, detail="Profile not found")
    return {"id": p.id, "name": p.name, "gender": p.gender, "height": p.height, "chest": p.chest, "shoulders": p.shoulders, "waist": p.waist, "hips": p.hips, "arm_length": p.arm_length, "leg_length": p.leg_length, "inseam": p.inseam}

@app.post("/api/profiles")
def create_or_update_profile(payload: models.BodyProfileCreate, db: Session = Depends(database.get_db)):
    existing = db.query(models.BodyProfile).filter(models.BodyProfile.name == payload.name).first()
    if existing:
        for k, v in payload.dict().items(): setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return {"status": "updated", "id": existing.id}

    p = models.BodyProfile(**payload.dict())
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"status": "created", "id": p.id}

@app.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: int, db: Session = Depends(database.get_db)):
    p = db.query(models.BodyProfile).filter(models.BodyProfile.id == profile_id).first()
    if p:
        db.delete(p)
        db.commit()
    return {"status": "deleted"}

@app.post("/api/calculate")
def calculate_for_profile(req: models.CalculateRequest, db: Session = Depends(database.get_db), limit: int = Query(30, ge=1, le=200)):
    profile = db.query(models.BodyProfile).filter(models.BodyProfile.id == req.profile_id).first()
    if not profile: raise HTTPException(status_code=404, detail="Profile not found")

    user = logic.Profile(
        height=profile.height or 175.0,
        chest=profile.chest or 100.0,
        waist=profile.waist or 85.0,
        hips=profile.hips or 100.0,
        shoulders=profile.shoulders or 45.0,
        arm_length=profile.arm_length or 62.0,
        outseam=profile.leg_length or 105.0,
        inseam=profile.inseam or 80.0
    )

    items = get_cached_items(db)
    results = []

    for item in items:
        metrics = item.metrics or {}
        theory = metrics.get("theory")
        if not theory: continue

        model_size = theory.get("model_size", "M")
        
        best_score = -1e18
        best_size = None
        best_explain = ""

        # ПРИНУДИТЕЛЬНЫЙ ПЕРЕБОР ВСЕХ РАЗМЕРОВ (XS -> 3XL)
        for size_label in logic.SIZES_ORDER:
            fit_res = logic.calculate_fit(user, model_size, theory, size_label)

            if fit_res.score > best_score:
                best_score = fit_res.score
                best_size = size_label
                explain_parts = [f"{fit_res.status} ({fit_res.score:.0f}%)"]
                explain_parts.extend(fit_res.details.values())
                explain_parts.extend(fit_res.warnings)
                best_explain = " | ".join(explain_parts)

        if best_size is None: continue

        results.append({
            "id": item.id,
            "sku": item.sku,
            "name": item.name,
            "platform": item.platform,
            "image_url": item.image_url,
            "price": item.price,
            "best_size": best_size,
            "score": float(best_score),
            "explain": best_explain,
            "metrics": metrics,
        })

    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results[:limit]

@app.post("/api/feedback")
def submit_feedback(fb: models.FeedbackSubmit, db: Session = Depends(database.get_db)):
    new_fb = models.Feedback(
        garment_id=fb.garment_id, 
        user_id=fb.user_id, 
        size_selected=fb.size_selected, 
        is_point_zero=fb.is_point_zero, 
        fit_matrix=fb.fit_matrix
    )
    db.add(new_fb)
    db.commit()

    analysis = None
    garment = db.query(models.Garment).filter(models.Garment.id == fb.garment_id).first()
    
    profile = None
    if fb.user_id and fb.user_id.isdigit():
        profile = db.query(models.BodyProfile).filter(models.BodyProfile.id == int(fb.user_id)).first()

    if garment and profile and garment.metrics:
        user = logic.Profile(
            height=profile.height or 175.0,
            chest=profile.chest or 100.0,
            waist=profile.waist or 85.0,
            hips=profile.hips or 100.0,
            shoulders=profile.shoulders or 45.0,
            arm_length=profile.arm_length or 62.0,
            outseam=profile.leg_length or 105.0,
            inseam=profile.inseam or 80.0
        )

        theory = garment.metrics.get("theory", {})
        ground_truth = garment.metrics.get("ground_truth", {})

        if theory:
            model_size = theory.get("model_size", "M")
            cat_type = theory.get("category_type", "top")
            fit_profile = theory.get("fit_profile", "regular")
            elastane = theory.get("elastane_pct", 0)

            best_t_score = -1
            best_t_size = None
            for sz in logic.SIZES_ORDER:
                res = logic.calculate_fit(user, model_size, theory, sz)
                if res.score > best_t_score:
                    best_t_score = res.score
                    best_t_size = sz

            best_gt_score = -1
            best_gt_size = None
            if ground_truth:
                ideal_ease = logic.DESIGN_EASE.get(fit_profile.lower(), logic.DESIGN_EASE['regular'])
                base_ease_chest = ideal_ease['top'] if cat_type.lower() == 'top' else ideal_ease['bottom']
                base_ease_waist = ideal_ease['bottom']
                base_ease_hips = ideal_ease['bottom']

                for gt_size, gt_meas in ground_truth.items():
                    fake_base_data = {
                        'category_type': cat_type,
                        'fit_profile': fit_profile,
                        'elastane_pct': elastane,
                        'height': theory.get('height', 175.0),
                        'sleeve_type': theory.get('sleeve_type', 'long'),
                        'leg_type': theory.get('leg_type', 'long'),
                    }
                    if 'chest' in gt_meas: fake_base_data['chest'] = gt_meas['chest'] - base_ease_chest
                    if 'waist' in gt_meas: fake_base_data['waist'] = gt_meas['waist'] - base_ease_waist
                    if 'hips' in gt_meas: fake_base_data['hips'] = gt_meas['hips'] - base_ease_hips
                    if 'inseam' in gt_meas: fake_base_data['g_inseam'] = gt_meas['inseam']

                    res = logic.calculate_fit(user, gt_size, fake_base_data, gt_size)
                    if res.score > best_gt_score:
                        best_gt_score = res.score
                        best_gt_size = gt_size

            analysis = {
                "theory_size": best_t_size,
                "theory_score": round(best_t_score),
                "gt_size": best_gt_size,
                "gt_score": round(best_gt_score) if best_gt_score != -1 else None,
                "match": (best_t_size == best_gt_size) if best_gt_size else None
            }

    return {"status": "success", "analysis": analysis}

@app.post("/api/admin/update-db")
def admin_update_db(db: Session = Depends(database.get_db)):
    invalidate_items_cache()
    count = db.query(models.Garment).count()
    return {"status": "ok", "garments_total": count, "stdout_tail": "Cache cleared manually", "stderr_tail": ""}

@app.get("/api/admin/stats")
def admin_stats(db: Session = Depends(database.get_db)):
    return {
        "counts": {
            "garments": db.query(models.Garment).count(),
            "profiles": db.query(models.BodyProfile).count(),
            "feedback": db.query(models.Feedback).count(),
            "priors": db.query(models.Prior).count()
        }
    }

@app.get("/api/admin/garments")
def admin_garments(search: str = Query(""), limit: int = Query(50), db: Session = Depends(database.get_db)):
    q = search.strip()
    query = db.query(models.Garment)
    if q: query = query.filter(or_(models.Garment.sku.ilike(f"%{q}%"), models.Garment.name.ilike(f"%{q}%")))
    items = query.order_by(models.Garment.id.desc()).limit(limit).all()
    return {"items": [garment_to_dict(g) for g in items]}

@app.get("/api/admin/builder/get")
def builder_get(sku: str = Query(...), db: Session = Depends(database.get_db)):
    g = db.query(models.Garment).filter(models.Garment.sku == sku.strip()).first()
    if not g: raise HTTPException(status_code=404, detail="not found")
    return garment_to_dict(g)

@app.get("/api/admin/builder/list")
def builder_list(limit: int = Query(20), db: Session = Depends(database.get_db)):
    items = db.query(models.Garment).order_by(models.Garment.id.desc()).limit(limit).all()
    return {"items": [garment_to_dict(g) for g in items]}

@app.post("/api/admin/builder/upsert")
def builder_upsert(payload: Dict[str, Any] = Body(...), db: Session = Depends(database.get_db)):
    sku = (payload.get("sku") or "").strip()
    if not sku: raise HTTPException(status_code=400, detail="sku is required")

    g = db.query(models.Garment).filter(models.Garment.sku == sku).first()
    created = False
    if not g:
        g = models.Garment(sku=sku)
        created = True

    g.name = (payload.get("name") or g.name or sku).strip()
    g.platform = (payload.get("platform") or g.platform or "manual").strip()
    if payload.get("image_url"): g.image_url = payload.get("image_url").strip()
    if payload.get("image_url_back"): g.image_url_back = payload.get("image_url_back").strip()
    
    pr = _coerce_float(payload.get("price"))
    if pr is not None: g.price = pr
    g.in_stock = bool(payload.get("in_stock", True))

    current_metrics = dict(g.metrics or {})
    if "theory" in payload: current_metrics["theory"] = payload["theory"]
    if "ground_truth" in payload: current_metrics["ground_truth"] = payload["ground_truth"]

    g.metrics = current_metrics

    db.add(g)
    db.commit()
    invalidate_items_cache()
    return {"ok": True, "action": "created" if created else "updated"}

@app.delete("/api/admin/builder/delete")
def builder_delete(sku: str = Query(...), db: Session = Depends(database.get_db)):
    g = db.query(models.Garment).filter(models.Garment.sku == sku.strip()).first()
    if g:
        db.query(models.Prior).filter(models.Prior.garment_id == g.id).delete()
        db.query(models.Feedback).filter(models.Feedback.garment_id == g.id).delete()
        db.delete(g)
        db.commit()
        invalidate_items_cache()
    return {"ok": True}

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/", include_in_schema=False)
def serve_index(): return FileResponse(INDEX_FILE)

@app.get("/index.js", include_in_schema=False)
def serve_index_js(): return FileResponse(INDEX_JS_FILE, media_type="application/javascript")

@app.get("/admin", include_in_schema=False)
def serve_admin(): return FileResponse(ADMIN_FILE)

@app.get("/admin.js", include_in_schema=False)
def serve_admin_js(): return FileResponse(ADMIN_JS_FILE, media_type="application/javascript")

@app.get("/builder", include_in_schema=False)
def serve_builder(): return FileResponse(BUILDER_FILE)

@app.get("/builder.js", include_in_schema=False)
def serve_builder_js(): return FileResponse(BUILDER_JS_FILE, media_type="application/javascript")

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)