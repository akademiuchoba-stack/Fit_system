import os
import sys
import logging
import subprocess
import dataclasses
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
from sqlalchemy.orm.attributes import flag_modified

from . import models, database, logic, calibration

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("fit_backend")

app = FastAPI(title="Fit_system API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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
        _ITEMS_CACHE["items"] = db.query(models.Garment).filter(models.Garment.in_stock == True).order_by(models.Garment.id.desc()).all()
        _ITEMS_CACHE["ts"] = now
    return _ITEMS_CACHE["items"]

def clean_dict(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}

def _coerce_float(x: Any) -> Optional[float]:
    try:
        if x is None: return None
        s = str(x).strip().replace(",", ".")
        if s == "": return None
        return float(s)
    except Exception:
        return None

def garment_to_dict(g: models.Garment) -> Dict[str, Any]:
    return {"id": g.id, "sku": g.sku, "name": g.name, "platform": g.platform, "image_url": g.image_url, "image_url_back": getattr(g, "image_url_back", None), "price": g.price, "in_stock": bool(g.in_stock), "metrics": g.metrics or {}}

@app.get("/api/profiles")
def list_profiles(db: Session = Depends(database.get_db)):
    profiles = db.query(models.BodyProfile).order_by(models.BodyProfile.updated_at.desc()).all()
    return [{
        "id": p.id, "name": p.name, "gender": p.gender, "height": p.height,
        "shoulders": p.shoulders, "back_width": p.back_width, "chest": p.chest, "underbust": p.underbust,
        "waist_top": p.waist_top, "belly": p.belly, "waist_bottom": p.waist_bottom, "high_hip": p.high_hip,
        "hips": p.hips, "thigh": p.thigh, "knee": p.knee, "calf": p.calf,
        "bicep": p.bicep, "neck": p.neck, "arm_length": p.arm_length,
        "leg_length": p.leg_length, "inseam": p.inseam, "length_dress": p.length_dress,
        "problem_zones": p.problem_zones or [], "comfort_C": p.comfort_C or {}
    } for p in profiles]

@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: int, db: Session = Depends(database.get_db)):
    p = db.query(models.BodyProfile).filter(models.BodyProfile.id == profile_id).first()
    if not p: raise HTTPException(status_code=404, detail="Profile not found")
    return {
        "id": p.id, "name": p.name, "gender": p.gender, "height": p.height,
        "shoulders": p.shoulders, "back_width": p.back_width, "chest": p.chest, "underbust": p.underbust,
        "waist_top": p.waist_top, "belly": p.belly, "waist_bottom": p.waist_bottom, "high_hip": p.high_hip,
        "hips": p.hips, "thigh": p.thigh, "knee": p.knee, "calf": p.calf,
        "bicep": p.bicep, "neck": p.neck, "arm_length": p.arm_length,
        "leg_length": p.leg_length, "inseam": p.inseam, "length_dress": p.length_dress,
        "problem_zones": p.problem_zones or [], "comfort_C": p.comfort_C or {}
    }

@app.post("/api/profiles")
def create_or_update_profile(payload: models.BodyProfileCreate, db: Session = Depends(database.get_db)):
    existing = db.query(models.BodyProfile).filter(models.BodyProfile.name == payload.name).first()
    if existing:
        for k, v in payload.dict().items(): setattr(existing, k, v)
        db.commit()
        return {"status": "updated", "id": existing.id}
    p = models.BodyProfile(**payload.dict())
    db.add(p); db.commit(); db.refresh(p)
    return {"status": "created", "id": p.id}

@app.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: int, db: Session = Depends(database.get_db)):
    p = db.query(models.BodyProfile).filter(models.BodyProfile.id == profile_id).first()
    if p: db.delete(p); db.commit()
    return {"status": "deleted"}

@app.post("/api/calculate")
def calculate_for_profile(req: models.CalculateRequest, db: Session = Depends(database.get_db), limit: int = Query(50)):
    profile = db.query(models.BodyProfile).filter(models.BodyProfile.id == req.profile_id).first()
    if not profile: raise HTTPException(status_code=404, detail="Profile not found")

    user = logic.Profile(
        height=getattr(profile, 'height', 175.0) or 175.0, shoulders=getattr(profile, 'shoulders', 0.0) or 0.0,
        back_width=getattr(profile, 'back_width', 0.0) or 0.0, chest=getattr(profile, 'chest', 0.0) or 0.0, underbust=getattr(profile, 'underbust', 0.0) or 0.0,
        waist_top=getattr(profile, 'waist_top', 0.0) or 0.0, belly=getattr(profile, 'belly', 0.0) or 0.0,
        waist_bottom=getattr(profile, 'waist_bottom', 0.0) or 0.0, high_hip=getattr(profile, 'high_hip', 0.0) or 0.0,
        hips=getattr(profile, 'hips', 0.0) or 0.0, thigh=getattr(profile, 'thigh', 0.0) or 0.0, knee=getattr(profile, 'knee', 0.0) or 0.0,
        calf=getattr(profile, 'calf', 0.0) or 0.0, bicep=getattr(profile, 'bicep', 0.0) or 0.0, neck=getattr(profile, 'neck', 0.0) or 0.0,
        arm_length=getattr(profile, 'arm_length', 0.0) or 0.0, outseam=getattr(profile, 'leg_length', 0.0) or 0.0,
        inseam=getattr(profile, 'inseam', 0.0) or 0.0, length_dress=getattr(profile, 'length_dress', 0.0) or 0.0,
        problem_zones=getattr(profile, 'problem_zones', []) or [], comfort_C=getattr(profile, 'comfort_C', {}) or {}
    )

    items = get_cached_items(db)
    results = []

    for item in items:
        metrics = item.metrics or {}
        theory = metrics.get("theory")
        
        if not theory:
            results.append({
                "id": item.id, "sku": item.sku, "name": item.name, "platform": item.platform,
                "image_url": item.image_url, "price": item.price, "best_size": "N/A",
                "score": 0.0, "explain": "⚠️ Требуется настроить Теорию (нажмите Builder)",
                "metrics": metrics, "available_sizes": [], "xray": []
            })
            continue

        try:
            safe_theory = clean_dict(theory)
            available_sizes = logic.SIZES_ORDER
            
            res_dict = logic.evaluate_all_sizes(user, safe_theory, available_sizes)
            best_size = res_dict["best_size"] or "N/A"
            best_res = next((r for r in res_dict["all_results"] if r.size_label == best_size), None)
            best_score = best_res.score if best_res else 0.0
            
            explain_parts = [f"{best_res.global_status} ({best_score:.0f}%)"] if best_res else ["МАЛО (0%)"]
            if best_res: explain_parts.extend(best_res.warnings)

            results.append({
                "id": item.id, "sku": item.sku, "name": item.name, "platform": item.platform,
                "image_url": item.image_url, "price": item.price, "best_size": best_size,
                "score": float(best_score), "explain": " | ".join(explain_parts),
                "metrics": metrics, "available_sizes": available_sizes,
                "xray": [dataclasses.asdict(r) for r in res_dict["all_results"]]
            })
        except Exception as e:
            logger.error(f"Calculate error for item {item.sku}: {e}")
            continue

    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results[:limit]

@app.post("/api/feedback")
def submit_feedback(fb: models.FeedbackSubmit, db: Session = Depends(database.get_db)):
    new_fb = models.Feedback(garment_id=fb.garment_id, user_id=fb.user_id, size_selected=fb.size_selected, is_point_zero=fb.is_point_zero, fit_matrix=fb.fit_matrix)
    db.add(new_fb); db.commit()

    analysis = None
    garment = db.query(models.Garment).filter(models.Garment.id == fb.garment_id).first()
    profile = db.query(models.BodyProfile).filter(models.BodyProfile.id == int(fb.user_id)).first() if fb.user_id and fb.user_id.isdigit() else None

    if garment and profile and garment.metrics:
        user = logic.Profile(
            height=getattr(profile, 'height', 175.0) or 175.0, shoulders=getattr(profile, 'shoulders', 0.0) or 0.0,
            back_width=getattr(profile, 'back_width', 0.0) or 0.0, chest=getattr(profile, 'chest', 0.0) or 0.0, underbust=getattr(profile, 'underbust', 0.0) or 0.0,
            waist_top=getattr(profile, 'waist_top', 0.0) or 0.0, belly=getattr(profile, 'belly', 0.0) or 0.0,
            waist_bottom=getattr(profile, 'waist_bottom', 0.0) or 0.0, high_hip=getattr(profile, 'high_hip', 0.0) or 0.0,
            hips=getattr(profile, 'hips', 0.0) or 0.0, thigh=getattr(profile, 'thigh', 0.0) or 0.0, knee=getattr(profile, 'knee', 0.0) or 0.0,
            calf=getattr(profile, 'calf', 0.0) or 0.0, bicep=getattr(profile, 'bicep', 0.0) or 0.0, neck=getattr(profile, 'neck', 0.0) or 0.0,
            arm_length=getattr(profile, 'arm_length', 0.0) or 0.0, outseam=getattr(profile, 'leg_length', 0.0) or 0.0,
            inseam=getattr(profile, 'inseam', 0.0) or 0.0, length_dress=getattr(profile, 'length_dress', 0.0) or 0.0,
            problem_zones=getattr(profile, 'problem_zones', []) or [], comfort_C=getattr(profile, 'comfort_C', {}) or {}
        )
        theory = garment.metrics.get("theory", {})
        ground_truth = garment.metrics.get("ground_truth", {})

        if theory:
            try:
                safe_theory = clean_dict(theory)
                t_res_dict = logic.evaluate_all_sizes(user, safe_theory, logic.SIZES_ORDER)
                best_t_size = t_res_dict["best_size"]
                best_t_res = next((r for r in t_res_dict["all_results"] if r.size_label == best_t_size), None)
                best_t_score = best_t_res.score if best_t_res else 0

                best_gt_score = -1; best_gt_size = None
                if ground_truth:
                    fit_profile = safe_theory.get("fit_profile", "regular")
                    cat_type = safe_theory.get("category_type", "top")
                    elastane = safe_theory.get("elastane_pct", 0)

                    ease_map = {'slim': (1.0, 0.5), 'regular': (3.0, 1.5), 'oversize': (7.0, 3.0)}
                    base_ease_top, base_ease_bot = ease_map.get(fit_profile.lower(), ease_map['regular'])
                    base_ease_chest = base_ease_top if cat_type.lower() == 'top' else base_ease_bot
                    base_ease_waist = base_ease_bot; base_ease_hips = base_ease_bot
                    user_flat = user.to_flat_half()

                    for gt_size, gt_meas in ground_truth.items():
                        fake_base_data = {
                            'category_type': cat_type, 'fit_profile': fit_profile, 'elastane_pct': elastane,
                            'height': safe_theory.get('height', 175.0), 'sleeve_type': safe_theory.get('sleeve_type', 'long'),
                            'leg_type': safe_theory.get('leg_type', 'long'),
                        }
                        if 'chest' in gt_meas: fake_base_data['chest'] = gt_meas['chest'] - (base_ease_chest * 2.0)
                        if 'waist' in gt_meas: fake_base_data['waist'] = gt_meas['waist'] - (base_ease_waist * 2.0)
                        if 'hips' in gt_meas: fake_base_data['hips'] = gt_meas['hips'] - (base_ease_hips * 2.0)
                        if 'inseam' in gt_meas: fake_base_data['g_inseam'] = gt_meas['inseam']

                        res = logic.calculate_single_size(user_flat, user, gt_size, fake_base_data, gt_size, True)
                        if res.score > best_gt_score:
                            best_gt_score = res.score
                            best_gt_size = gt_size

                analysis = {
                    "theory_size": best_t_size, "theory_score": round(best_t_score),
                    "gt_size": best_gt_size, "gt_score": round(best_gt_score) if best_gt_score != -1 else None,
                    "match": (best_t_size == best_gt_size) if best_gt_size else None,
                    "xray": [dataclasses.asdict(r) for r in t_res_dict["all_results"]]
                }
            except Exception as e:
                logger.error(f"Feedback calculation error: {e}")

    return {"status": "success", "analysis": analysis}

@app.post("/api/admin/update-db")
def admin_update_db(db: Session = Depends(database.get_db)):
    invalidate_items_cache()
    count = db.query(models.Garment).count()
    return {"status": "ok", "garments_total": count, "stdout_tail": "Cache cleared manually", "stderr_tail": ""}

@app.get("/api/admin/stats")
def admin_stats(db: Session = Depends(database.get_db)):
    return {"counts": {"garments": db.query(models.Garment).count(), "profiles": db.query(models.BodyProfile).count(), "feedback": db.query(models.Feedback).count(), "priors": db.query(models.Prior).count()}}

@app.get("/api/admin/garments")
def admin_garments(search: str = Query(""), limit: int = Query(50), db: Session = Depends(database.get_db)):
    q = search.strip()
    query = db.query(models.Garment)
    if q: query = query.filter(or_(models.Garment.sku.ilike(f"%{q}%"), models.Garment.name.ilike(f"%{q}%")))
    return {"items": [garment_to_dict(g) for g in query.order_by(models.Garment.id.desc()).limit(limit).all()]}

@app.get("/api/admin/builder/get")
def builder_get(sku: str = Query(...), db: Session = Depends(database.get_db)):
    g = db.query(models.Garment).filter(models.Garment.sku == sku.strip()).first()
    if not g: raise HTTPException(status_code=404, detail="not found")
    return garment_to_dict(g)

@app.get("/api/admin/builder/list")
def builder_list(limit: int = Query(20), db: Session = Depends(database.get_db)):
    return {"items": [garment_to_dict(g) for g in db.query(models.Garment).order_by(models.Garment.id.desc()).limit(limit).all()]}

# === ЖЕЛЕЗОБЕТОННОЕ СОХРАНЕНИЕ: НЕ ЗАТИРАЕТ СТАРЫЕ ДАННЫЕ ===
@app.post("/api/admin/builder/upsert")
def builder_upsert(payload: Dict[str, Any] = Body(...), db: Session = Depends(database.get_db)):
    sku = (payload.get("sku") or "").strip()
    if not sku: raise HTTPException(status_code=400, detail="sku is required")

    g = db.query(models.Garment).filter(models.Garment.sku == sku).first()
    created = False
    if not g:
        g = models.Garment(sku=sku)
        db.add(g)
        created = True

    # Обновляем текстовые поля, ТОЛЬКО если с фронта пришла непустая строка.
    new_name = payload.get("name", "").strip()
    if new_name:
        g.name = new_name
    elif not g.name:
        g.name = sku
        
    new_platform = payload.get("platform", "").strip()
    if new_platform:
        g.platform = new_platform
    elif not g.platform:
        g.platform = "manual"
        
    new_img = payload.get("image_url", "").strip()
    if new_img: g.image_url = new_img
        
    new_img_back = payload.get("image_url_back", "").strip()
    if new_img_back: g.image_url_back = new_img_back
    
    if payload.get("price"):
        g.price = _coerce_float(payload["price"])
        
    if "in_stock" in payload:
        g.in_stock = bool(payload["in_stock"])

    current_metrics = g.metrics or {}
    new_metrics = dict(current_metrics) 
    
    if "theory" in payload: new_metrics["theory"] = payload["theory"]
    if "ground_truth" in payload: new_metrics["ground_truth"] = payload["ground_truth"]

    g.metrics = new_metrics
    flag_modified(g, "metrics") 
    
    db.commit()
    invalidate_items_cache()
    return {"ok": True, "action": "created" if created else "updated"}

@app.delete("/api/admin/builder/delete")
def builder_delete(sku: str = Query(...), db: Session = Depends(database.get_db)):
    g = db.query(models.Garment).filter(models.Garment.sku == sku.strip()).first()
    if g:
        db.query(models.Prior).filter(models.Prior.garment_id == g.id).delete()
        db.query(models.Feedback).filter(models.Feedback.garment_id == g.id).delete()
        db.delete(g); db.commit(); invalidate_items_cache()
    return {"ok": True}

if FRONTEND_DIR.exists(): app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
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

if __name__ == "__main__": uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)