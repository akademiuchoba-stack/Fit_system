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
app = FastAPI(title="Fit_system API", version="1.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# PATHS
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
SHOPS_DIR = BASE_DIR / "shops"
SHOP_DB_PATH = SHOPS_DIR / "shop.db"

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
        if x is None:
            return None
        s = str(x).strip().replace(",", ".")
        if s == "":
            return None
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


# -----------------------------
# HEALTH
# -----------------------------
@app.get("/api/health")
def api_health():
    return {"status": "ok"}


# -----------------------------
# ITEMS (JSON SAFE)
# -----------------------------
@app.get("/api/items")
def get_items(db: Session = Depends(database.get_db)):
    try:
        items = get_cached_items(db)
        return [garment_to_dict(g) for g in items]
    except Exception as e:
        logger.exception("Error fetching items")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# PROFILES CRUD
# -----------------------------
@app.get("/api/profiles")
def list_profiles(db: Session = Depends(database.get_db)):
    profiles = db.query(models.BodyProfile).order_by(models.BodyProfile.updated_at.desc()).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "gender": p.gender,
            "height": p.height,
            "chest": p.chest,
            "shoulders": p.shoulders,
            "waist": p.waist,
            "hips": p.hips,
            "arm_length": p.arm_length,
            "leg_length": p.leg_length,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        for p in profiles
    ]


@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: int, db: Session = Depends(database.get_db)):
    p = db.query(models.BodyProfile).filter(models.BodyProfile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {
        "id": p.id,
        "name": p.name,
        "gender": p.gender,
        "height": p.height,
        "chest": p.chest,
        "shoulders": p.shoulders,
        "waist": p.waist,
        "hips": p.hips,
        "arm_length": p.arm_length,
        "leg_length": p.leg_length,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@app.post("/api/profiles")
def create_or_update_profile(payload: models.BodyProfileCreate, db: Session = Depends(database.get_db)):
    existing = db.query(models.BodyProfile).filter(models.BodyProfile.name == payload.name).first()
    if existing:
        for k, v in payload.dict().items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return {"status": "updated", "id": existing.id}

    p = models.BodyProfile(**payload.dict())
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"status": "created", "id": p.id}


@app.put("/api/profiles/{profile_id}")
def update_profile(profile_id: int, payload: models.BodyProfileUpdate, db: Session = Depends(database.get_db)):
    p = db.query(models.BodyProfile).filter(models.BodyProfile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")

    data = payload.dict(exclude_unset=True)
    if "name" in data and data["name"]:
        conflict = (
            db.query(models.BodyProfile)
            .filter(models.BodyProfile.name == data["name"], models.BodyProfile.id != profile_id)
            .first()
        )
        if conflict:
            raise HTTPException(status_code=409, detail="Profile name already exists")

    for k, v in data.items():
        setattr(p, k, v)

    db.commit()
    db.refresh(p)
    return {"status": "updated", "id": p.id}


@app.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: int, db: Session = Depends(database.get_db)):
    p = db.query(models.BodyProfile).filter(models.BodyProfile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    db.delete(p)
    db.commit()
    return {"status": "deleted"}


# -----------------------------
# CALCULATE (FOR FRONT CARDS)
# -----------------------------
@app.post("/api/calculate")
def calculate_for_profile(
    req: models.CalculateRequest,
    db: Session = Depends(database.get_db),
    limit: int = Query(30, ge=1, le=200),
):
    profile = db.query(models.BodyProfile).filter(models.BodyProfile.id == req.profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    user_data = {
        "name": profile.name,
        "gender": profile.gender,
        "height": profile.height,
        "chest": profile.chest,
        "shoulders": profile.shoulders,
        "waist": profile.waist,
        "hips": profile.hips,
        "arm_length": profile.arm_length,
        "leg_length": profile.leg_length,
    }

    items = get_cached_items(db)
    results: List[Dict[str, Any]] = []

    for item in items:
        all_sizes = item.metrics or {}
        if not isinstance(all_sizes, dict) or not all_sizes:
            continue

        best_score = -1e18
        best_size = None
        best_explain = ""
        best_metrics = None

        for size_label, m in all_sizes.items():
            if not isinstance(m, dict):
                continue

            m_norm = dict(m)
            # подстраховка по ключам
            if "shoulder" in m_norm and "shoulders" not in m_norm:
                m_norm["shoulders"] = m_norm["shoulder"]

            garment_payload = {
                "id": item.id,
                "sku": item.sku,
                "name": item.name,
                "platform": item.platform,
                "image_url": item.image_url,
                "metrics": m_norm,
                "fit_profile": (m_norm.get("fit_profile") or "regular"),
                "fabric": (m_norm.get("fabric") or ""),
                "elastane_pct": m_norm.get("elastane_pct"),
                "model_metrics": m_norm.get("model_metrics"),
                "model_size": m_norm.get("model_size"),
            }

            fit_res = logic.compute_fit_score(user_data, garment_payload, size_label=str(size_label))

            if fit_res.score > best_score:
                best_score = fit_res.score
                best_size = str(size_label)
                best_explain = fit_res.explanation or ""
                best_metrics = m_norm

        if best_size is None:
            continue

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
            "metrics": best_metrics or {},
        })

    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results[:limit]


# -----------------------------
# FEEDBACK
# -----------------------------
@app.post("/api/feedback")
def submit_feedback(fb: models.FeedbackSubmit, db: Session = Depends(database.get_db)):
    # user_id в модели может быть str, а фронт шлёт int → приводим к str
    user_id_str = str(fb.user_id)

    new_fb = models.Feedback(
        garment_id=fb.garment_id,
        user_id=user_id_str,
        size_selected=fb.size_selected,
        judgment=fb.judgment,
        real_measurements=fb.real_measurements,
    )
    db.add(new_fb)

    # байес-апдейт по груди (если есть)
    if fb.real_measurements:
        garment = db.query(models.Garment).filter(models.Garment.id == fb.garment_id).first()
        prior = (
            db.query(models.Prior)
            .filter(models.Prior.garment_id == fb.garment_id, models.Prior.size_label == fb.size_selected)
            .first()
        )
        if prior and garment and isinstance(fb.real_measurements, dict) and ("chest" in fb.real_measurements):
            new_mu, new_sigma = calibration.bayesian_update(
                prior.mu_chest, prior.sigma_chest, fb.real_measurements["chest"]
            )
            prior.mu_chest = new_mu
            prior.sigma_chest = new_sigma

            updated_metrics = dict(garment.metrics or {})
            updated_metrics.setdefault(fb.size_selected, {})
            if isinstance(updated_metrics[fb.size_selected], dict):
                updated_metrics[fb.size_selected]["chest"] = new_mu
            garment.metrics = updated_metrics

    db.commit()
    return {"status": "success"}


# -----------------------------
# ADMIN: UPDATE DB (RUN PARSER AND WAIT)
# -----------------------------
@app.post("/api/admin/update-db")
def admin_update_db(db: Session = Depends(database.get_db)):
    SHOPS_DIR.mkdir(parents=True, exist_ok=True)

    parser_script = SHOPS_DIR / "ostin_parser.py"
    if not parser_script.exists():
        raise HTTPException(status_code=500, detail=f"Parser script not found: {parser_script}")

    python_bin = sys.executable
    timeout_sec = int(os.getenv("FIT_PARSER_TIMEOUT", "900"))
    cmd = [python_bin, str(parser_script), "--db", str(SHOP_DB_PATH)]

    logger.info("Running parser: %s", " ".join(cmd))

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail=f"Parser timeout after {timeout_sec}s")

    out_tail = (proc.stdout or "")[-4000:]
    err_tail = (proc.stderr or "")[-4000:]

    if proc.returncode != 0:
        logger.error("Parser failed rc=%s stderr_tail=%s", proc.returncode, err_tail)
        raise HTTPException(status_code=500, detail=f"Parser failed rc={proc.returncode}. {err_tail}")

    invalidate_items_cache()
    count = db.query(models.Garment).count()
    return {"status": "ok", "garments_total": count, "stdout_tail": out_tail, "stderr_tail": err_tail}


# -----------------------------
# ADMIN: STATS / TABLES
# -----------------------------
@app.get("/api/admin/stats")
def admin_stats(db: Session = Depends(database.get_db)):
    garments = db.query(models.Garment).count()
    profiles = db.query(models.BodyProfile).count()
    feedback = db.query(models.Feedback).count()
    priors = db.query(models.Prior).count()

    db_path = getattr(database, "DB_PATH", None)
    db_size = None
    try:
        if db_path and os.path.exists(db_path):
            db_size = os.path.getsize(db_path)
    except Exception:
        db_size = None

    return {
        "counts": {"garments": garments, "profiles": profiles, "feedback": feedback, "priors": priors},
        "db": {"path": db_path, "size_bytes": db_size},
    }


@app.get("/api/admin/tables")
def admin_tables(db: Session = Depends(database.get_db)):
    engine = db.get_bind()
    insp = inspect(engine)
    names = insp.get_table_names()
    out = []
    for name in names:
        try:
            cnt = db.execute(text(f"SELECT COUNT(*) AS c FROM {name}")).scalar()
            out.append({"name": name, "rows": int(cnt or 0)})
        except Exception:
            out.append({"name": name, "rows": None})
    out.sort(key=lambda x: x["name"])
    return {"tables": out}


@app.get("/api/admin/table/{table_name}")
def admin_table_preview(table_name: str, limit: int = 50, db: Session = Depends(database.get_db)):
    engine = db.get_bind()
    insp = inspect(engine)
    allowed = set(insp.get_table_names())
    if table_name not in allowed:
        raise HTTPException(status_code=404, detail="Unknown table")

    lim = max(1, min(int(limit or 50), 200))
    rows = db.execute(text(f"SELECT * FROM {table_name} LIMIT :lim"), {"lim": lim}).mappings().all()
    return {"rows": [dict(r) for r in rows]}


@app.get("/api/admin/feedback")
def admin_feedback(limit: int = 100, db: Session = Depends(database.get_db)):
    lim = max(1, min(int(limit or 100), 500))
    items = db.query(models.Feedback).order_by(models.Feedback.id.desc()).limit(lim).all()
    return {"items": [feedback_to_dict(f) for f in items]}


# -----------------------------
# ADMIN: GARMENTS LIST (FOR ADMIN.JS)
# -----------------------------
@app.get("/api/admin/garments")
def admin_garments(
    search: str = Query("", description="search by sku or name"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(database.get_db),
):
    q = (search or "").strip()
    query = db.query(models.Garment)

    if q:
        # ilike может не работать в sqlite с кириллицей идеально, но для sku/латиницы ок
        like = f"%{q}%"
        query = query.filter(or_(models.Garment.sku.ilike(like), models.Garment.name.ilike(like)))

    items = query.order_by(models.Garment.id.desc()).limit(int(limit)).all()
    return {"items": [garment_to_dict(g) for g in items]}


# -----------------------------
# ADMIN: BUILDER API (GET/UPSERT/LIST/DELETE)
# -----------------------------
@app.get("/api/admin/builder/get")
def builder_get(sku: str = Query(...), db: Session = Depends(database.get_db)):
    s = (sku or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="sku required")
    g = db.query(models.Garment).filter(models.Garment.sku == s).first()
    if not g:
        raise HTTPException(status_code=404, detail="not found")
    return garment_to_dict(g)


@app.get("/api/admin/builder/list")
def builder_list(limit: int = Query(20, ge=1, le=200), db: Session = Depends(database.get_db)):
    items = db.query(models.Garment).order_by(models.Garment.id.desc()).limit(int(limit)).all()
    return {"items": [garment_to_dict(g) for g in items]}


@app.post("/api/admin/builder/upsert")
def builder_upsert(payload: Dict[str, Any] = Body(...), db: Session = Depends(database.get_db)):
    sku = (payload.get("sku") or "").strip()
    if not sku:
        raise HTTPException(status_code=400, detail="sku is required")

    g = db.query(models.Garment).filter(models.Garment.sku == sku).first()
    created = False
    if not g:
        g = models.Garment(sku=sku)
        created = True

    # базовые поля
    g.name = (payload.get("name") or g.name or sku).strip()
    g.platform = (payload.get("platform") or g.platform or "manual").strip()

    img = (payload.get("image_url") or "").strip()
    if img:
        g.image_url = img

    pr = _coerce_float(payload.get("price"))
    if pr is not None:
        g.price = float(pr)

    g.in_stock = bool(payload.get("in_stock", True))

    # размерный блок в metrics
    size_label = (payload.get("size_label") or "M").strip().upper()
    allm = dict(g.metrics or {})
    allm.setdefault(size_label, {})
    block = dict(allm.get(size_label) or {})

    rm = payload.get("real_measurements")
    if isinstance(rm, dict):
        block["real_measurements"] = rm

    tr = payload.get("try_on")
    if isinstance(tr, dict):
        block["try_on"] = tr

    # дополнительные полезные поля — не ломают твою логику
    for key in ["fit_profile", "fabric", "elastane_pct", "model_metrics", "model_size", "internal_category"]:
        if payload.get(key) is not None:
            block[key] = payload.get(key)

    allm[size_label] = block
    g.metrics = allm

    db.add(g)
    db.commit()
    db.refresh(g)
    invalidate_items_cache()

    return {"ok": True, "action": "created" if created else "updated", "sku": sku, "id": g.id, "size": size_label}


@app.delete("/api/admin/builder/delete")
def builder_delete(sku: str = Query(...), db: Session = Depends(database.get_db)):
    s = (sku or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="sku required")

    g = db.query(models.Garment).filter(models.Garment.sku == s).first()
    if not g:
        raise HTTPException(status_code=404, detail="not found")

    db.delete(g)
    db.commit()
    invalidate_items_cache()
    return {"ok": True, "deleted": s}


# -----------------------------
# FRONTEND STATIC + ROUTES
# -----------------------------
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_index():
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)
    raise HTTPException(status_code=404, detail="Frontend index.html not found")


@app.get("/index.js", include_in_schema=False)
def serve_index_js():
    if INDEX_JS_FILE.exists():
        return FileResponse(INDEX_JS_FILE, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Frontend index.js not found")


@app.get("/admin", include_in_schema=False)
def serve_admin():
    if ADMIN_FILE.exists():
        return FileResponse(ADMIN_FILE)
    raise HTTPException(status_code=404, detail="Frontend admin.html not found")


@app.get("/admin.js", include_in_schema=False)
def serve_admin_js():
    if ADMIN_JS_FILE.exists():
        return FileResponse(ADMIN_JS_FILE, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Frontend admin.js not found")


@app.get("/builder", include_in_schema=False)
def serve_builder():
    if BUILDER_FILE.exists():
        return FileResponse(BUILDER_FILE)
    raise HTTPException(status_code=404, detail="Frontend builder.html not found")


@app.get("/builder.js", include_in_schema=False)
def serve_builder_js():
    if BUILDER_JS_FILE.exists():
        return FileResponse(BUILDER_JS_FILE, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Frontend builder.js not found")


# -----------------------------
# LOCAL RUN
# -----------------------------
if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)





