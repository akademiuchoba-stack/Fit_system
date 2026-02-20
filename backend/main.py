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

# -----------------------------
# FASTAPI APP
# -----------------------------
app = FastAPI(title="Fit_system API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# PATHS
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

INDEX_FILE = FRONTEND_DIR / "index.html"
INDEX_JS_FILE = FRONTEND_DIR / "index.js"
ADMIN_FILE = FRONTEND_DIR / "admin.html"
ADMIN_JS_FILE = FRONTEND_DIR / "admin.js"
BUILDER_FILE = FRONTEND_DIR / "builder.html"
BUILDER_JS_FILE = FRONTEND_DIR / "builder.js"

# -----------------------------
# INIT DB
# -----------------------------
models.Base.metadata.create_all(bind=database.engine)

# -----------------------------
# CACHE ITEMS
# -----------------------------
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
        "price": g.price,
        "in_stock": bool(g.in_stock),
        "metrics": g.metrics or {},
    }

def feedback_to_dict(f: models.Feedback) -> Dict[str, Any]:
    return {
        "id": getattr(f, "id", None),
        "garment_id": getattr(f, "garment_id", None),
        "user_id": getattr(f, "user_id", None),
        "size_selected": getattr(f, "size_selected", None),
        "judgment": getattr(f, "judgment", None),
        "real_measurements": getattr(f, "real_measurements", None),
        "created_at": getattr(f, "created_at", None).isoformat() if getattr(f, "created_at", None) else None,
    }

# --- ИНТЕГРАЦИЯ ЛОГИКИ ИЗ debug_feed.py ---
def get_best_value(field, metrics, is_biometry=False):
    main_key = None
    for k in metrics.keys():
        if k not in ['size_chart', 'sources'] and isinstance(metrics[k], dict):
            main_key = k
            break
            
    if not main_key: return None
    work_zone = metrics[main_key]
    
    sources = [work_zone]
    if is_biometry:
        sources = [work_zone.get('model_metrics', {})]

    for src in sources:
        if not isinstance(src, dict): continue
        val = src.get(field)
        if val:
            if is_biometry or field == 'elastane_pct':
                try: return float(val)
                except: pass
            else:
                return str(val)
    return None

def extract_smart_model(metrics: dict):
    model_size = get_best_value('model_size', metrics) or 'M'
    chest = get_best_value('chest', metrics, True)
    waist = get_best_value('waist', metrics, True)
    hips = get_best_value('hips', metrics, True)
    height = get_best_value('height', metrics, True)
    
    smart_data = {
        'chest': chest or 90.0,
        'waist': waist or 70.0,
        'hips': hips or 95.0,
        'height': height or 175.0,
        'fit_profile': get_best_value('fit_profile', metrics) or 'regular',
        'category_type': get_best_value('category_type', metrics) or 'top',
        'elastane_pct': get_best_value('elastane_pct', metrics) or 0.0,
    }
    return model_size, smart_data

# -----------------------------
# SYSTEM: WEBHOOK DEPLOY
# -----------------------------
@app.post("/api/webhook-deploy")
def webhook_deploy():
    """
    Эндпоинт для автоматического деплоя из GitHub.
    Выполняет git pull и перезапускает systemd сервис.
    """
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

# -----------------------------
# PROFILES CRUD
# -----------------------------
@app.get("/api/profiles")
def list_profiles(db: Session = Depends(database.get_db)):
    profiles = db.query(models.BodyProfile).order_by(models.BodyProfile.updated_at.desc()).all()
    return [{"id": p.id, "name": p.name, "gender": p.gender, "height": p.height, "chest": p.chest, "shoulders": p.shoulders, "waist": p.waist, "hips": p.hips, "arm_length": p.arm_length, "leg_length": p.leg_length} for p in profiles]

@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: int, db: Session = Depends(database.get_db)):
    p = db.query(models.BodyProfile).filter(models.BodyProfile.id == profile_id).first()
    if not p: raise HTTPException(status_code=404, detail="Profile not found")
    return {"id": p.id, "name": p.name, "gender": p.gender, "height": p.height, "chest": p.chest, "shoulders": p.shoulders, "waist": p.waist, "hips": p.hips, "arm_length": p.arm_length, "leg_length": p.leg_length}

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

# -----------------------------
# CALCULATE (FOR FRONT CARDS)
# -----------------------------
@app.post("/api/calculate")
def calculate_for_profile(req: models.CalculateRequest, db: Session = Depends(database.get_db), limit: int = Query(30, ge=1, le=200)):
    profile = db.query(models.BodyProfile).filter(models.BodyProfile.id == req.profile_id).first()
    if not profile: raise HTTPException(status_code=404, detail="Profile not found")

    # Собираем пользователя под новый формат logic.Profile (с расчетом шагового шва)
    user = logic.Profile(
        height=profile.height or 175.0,
        chest=profile.chest or 100.0,
        waist=profile.waist or 85.0,
        hips=profile.hips or 100.0,
        shoulders=profile.shoulders or 45.0,
        arm_length=profile.arm_length or 62.0,
        outseam=profile.leg_length or 105.0,
        inseam=(profile.leg_length - 25) if profile.leg_length else 80.0
    )

    items = get_cached_items(db)
    results = []

    for item in items:
        all_sizes = item.metrics or {}
        if not isinstance(all_sizes, dict) or not all_sizes: continue

        model_size, base_data = extract_smart_model(all_sizes)
        
        best_score = -1e18
        best_size = None
        best_explain = ""

        # Перебираем доступные размеры вещи из базы
        for size_label in all_sizes.keys():
            fit_res = logic.calculate_fit(user, model_size, base_data, size_label)

            if fit_res.score > best_score:
                best_score = fit_res.score
                best_size = size_label
                # Собираем пояснения в одну строку для фронта
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
            "metrics": all_sizes.get(best_size, {}),
        })

    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results[:limit]

# -----------------------------
# FEEDBACK (МАТРИЦА ПРИМЕРКИ)
# -----------------------------
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
    return {"status": "success"}

# -----------------------------
# ADMIN: CLEAR CACHE (Replacement for update-db)
# -----------------------------
@app.post("/api/admin/update-db")
def admin_update_db(db: Session = Depends(database.get_db)):
    invalidate_items_cache()
    count = db.query(models.Garment).count()
    return {"status": "ok", "garments_total": count, "stdout_tail": "Cache cleared manually", "stderr_tail": ""}

# -----------------------------
# ADMIN: STATS & LIST
# -----------------------------
@app.get("/api/admin/stats")
def admin_stats(db: Session = Depends(database.get_db)):
    return {
        "counts": {
            "garments": db.query(models.Garment).count(),
            "profiles": db.query(models.BodyProfile).count(),
            "feedback": db.query(models.Feedback).count(),
            "priors": db.query(models.Prior).count()
        },
        "db": {"path": getattr(database, "DB_PATH", None), "size_bytes": os.path.getsize(getattr(database, "DB_PATH", "")) if getattr(database, "DB_PATH", None) and os.path.exists(getattr(database, "DB_PATH", "")) else None}
    }

@app.get("/api/admin/garments")
def admin_garments(search: str = Query(""), limit: int = Query(50), db: Session = Depends(database.get_db)):
    q = search.strip()
    query = db.query(models.Garment)
    if q: query = query.filter(or_(models.Garment.sku.ilike(f"%{q}%"), models.Garment.name.ilike(f"%{q}%")))
    items = query.order_by(models.Garment.id.desc()).limit(limit).all()
    return {"items": [garment_to_dict(g) for g in items]}

# -----------------------------
# BUILDER API
# -----------------------------
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

    # 1. Основное (Идентификация)
    g.name = (payload.get("name") or g.name or sku).strip()
    g.platform = (payload.get("platform") or g.platform or "manual").strip()
    if payload.get("image_url"): g.image_url = payload.get("image_url").strip()
    if payload.get("image_url_back"): g.image_url_back = payload.get("image_url_back").strip()
    
    pr = _coerce_float(payload.get("price"))
    if pr is not None: g.price = pr
    g.in_stock = bool(payload.get("in_stock", True))

    # 2. Формируем JSON структуру metrics (Теория + Истина)
    current_metrics = dict(g.metrics or {})
    
    # Сохраняем теоретические данные (с сайта)
    if "theory" in payload:
        current_metrics["theory"] = payload["theory"]
        
    # Сохраняем практические данные рулетки (ground_truth)
    if "ground_truth" in payload:
        current_metrics["ground_truth"] = payload["ground_truth"]

    g.metrics = current_metrics

    db.add(g)
    db.commit()
    invalidate_items_cache()
    return {"ok": True, "action": "created" if created else "updated"}

@app.delete("/api/admin/builder/delete")
def builder_delete(sku: str = Query(...), db: Session = Depends(database.get_db)):
    g = db.query(models.Garment).filter(models.Garment.sku == sku.strip()).first()
    if g:
        # Удаляем привязанные оценки и отзывы, чтобы не было ошибки FOREIGN KEY constraint failed
        db.query(models.Prior).filter(models.Prior.garment_id == g.id).delete()
        db.query(models.Feedback).filter(models.Feedback.garment_id == g.id).delete()
        
        db.delete(g)
        db.commit()
        invalidate_items_cache()
    return {"ok": True}

# -----------------------------
# FRONTEND STATIC + ROUTES
# -----------------------------
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