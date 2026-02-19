import os
import sys
import logging
import subprocess
from pathlib import Path
from time import time
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect

from . import models, database, logic, parser, calibration

# -----------------------------
# ЛОГИРОВАНИЕ
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# -----------------------------
# FASTAPI
# -----------------------------
app = FastAPI(title="Fit_system API", version="1.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# ПУТИ
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
INDEX_FILE = FRONTEND_DIR / "index.html"
INDEX_JS_FILE = FRONTEND_DIR / "index.js"
ADMIN_FILE = FRONTEND_DIR / "admin.html"
ADMIN_JS_FILE = FRONTEND_DIR / "admin.js"

# Ручной сборщик (если файлы есть)
BUILDER_FILE = FRONTEND_DIR / "builder.html"
BUILDER_JS_FILE = FRONTEND_DIR / "builder.js"

# shops/shop.db (используется database.py по умолчанию)
SHOPS_DIR = BASE_DIR / "shops"
SHOP_DB_PATH = SHOPS_DIR / "shop.db"

# -----------------------------
# ИНИЦИАЛИЗАЦИЯ БД
# -----------------------------
models.Base.metadata.create_all(bind=database.engine)

# -----------------------------
# КЭШ ТОВАРОВ
# -----------------------------
_ITEMS_CACHE = {"ts": 0.0, "items": None}
CACHE_TTL_SEC = int(os.getenv("FIT_ITEMS_CACHE_TTL", "10"))


def get_cached_items(db: Session):
    now = time()
    if _ITEMS_CACHE["items"] is None or (now - _ITEMS_CACHE["ts"]) > CACHE_TTL_SEC:
        items = db.query(models.Garment).filter(models.Garment.in_stock == True).all()
        _ITEMS_CACHE["items"] = items
        _ITEMS_CACHE["ts"] = now
    return _ITEMS_CACHE["items"]


def invalidate_items_cache():
    _ITEMS_CACHE["items"] = None
    _ITEMS_CACHE["ts"] = 0.0


# -----------------------------
# HEALTH
# -----------------------------
@app.get("/api/health")
def api_health():
    return {"status": "ok"}


# -----------------------------
# API ITEMS
# -----------------------------
@app.get("/api/items")
def get_items(db: Session = Depends(database.get_db)):
    try:
        items = get_cached_items(db)
        return items
    except Exception as e:
        logger.error(f"Error fetching items: {e}")
        raise HTTPException(status_code=500, detail="Database error")


# -----------------------------
# PROFILES
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
# CALCULATE
# -----------------------------
@app.post("/api/calculate")
def calculate_for_profile(
    req: models.CalculateRequest,
    db: Session = Depends(database.get_db),
    limit: int = Query(20, ge=1, le=200),
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
        "arm": profile.arm_length,
        "leg": profile.leg_length,
    }

    items = get_cached_items(db)

    def normalize_item_metrics(m: dict) -> dict:
        mm = dict(m or {})
        for k in ("chest", "waist", "hips"):
            v = mm.get(k)
            try:
                v = float(v)
            except Exception:
                continue
            u = user_data.get(k)
            if u and u > 90 and v < 80:
                mm[k] = v * 2.0
        if "shoulder" in mm and "shoulders" not in mm:
            mm["shoulders"] = mm.pop("shoulder")
        return mm

    results = []

    for item in items:
        if not item.metrics:
            continue

        best = None
        best_score = -1.0

        for size_label, raw_metrics in (item.metrics or {}).items():
            m_norm = normalize_item_metrics(raw_metrics or {})
            garment_payload = {
                "id": item.id,
                "sku": item.sku,
                "name": item.name,
                "platform": item.platform,
                "image_url": item.image_url,
                "fit_profile": (m_norm.get("fit_profile") or "regular"),
                "fabric": (m_norm.get("fabric") or ""),
                "elastane_pct": m_norm.get("elastane_pct"),
                "model_metrics": m_norm.get("model_metrics"),
                "model_size": m_norm.get("model_size"),
                "metrics": m_norm,
            }

            fit_res = logic.compute_fit_score(user_data, garment_payload, size_label=str(size_label))
            if fit_res.score > best_score:
                best_score = fit_res.score
                best = {
                    "item_id": item.id,
                    "sku": item.sku,
                    "name": item.name,
                    "platform": item.platform,
                    "image": item.image_url,
                    "size": str(size_label),
                    "fit": {
                        "score": round(fit_res.score, 2),
                        "status": fit_res.status,
                        "explanation": fit_res.explanation,
                        "deltas_cm": fit_res.deltas_cm,
                        "warnings": fit_res.warnings,
                    },
                    "metrics": m_norm,
                }

        if best:
            results.append(best)

    results.sort(key=lambda x: x["fit"]["score"], reverse=True)
    return results[:limit]


# -----------------------------
# FEEDBACK
# -----------------------------
@app.post("/api/feedback")
def submit_feedback(fb: models.FeedbackSubmit, db: Session = Depends(database.get_db)):
    new_fb = models.Feedback(
        garment_id=fb.garment_id,
        user_id=fb.user_id,
        size_selected=fb.size_selected,
        judgment=fb.judgment,
        real_measurements=fb.real_measurements,
    )
    db.add(new_fb)

    if fb.real_measurements:
        garment = db.query(models.Garment).filter(models.Garment.id == fb.garment_id).first()
        prior = (
            db.query(models.Prior)
            .filter(models.Prior.garment_id == fb.garment_id, models.Prior.size_label == fb.size_selected)
            .first()
        )

        if prior and "chest" in fb.real_measurements:
            new_mu, new_sigma = calibration.bayesian_update(
                prior.mu_chest, prior.sigma_chest, fb.real_measurements["chest"]
            )
            prior.mu_chest = new_mu
            prior.sigma_chest = new_sigma

            updated_metrics = dict(garment.metrics or {})
            updated_metrics.setdefault(fb.size_selected, {})
            updated_metrics[fb.size_selected]["chest"] = new_mu
            garment.metrics = updated_metrics

    db.commit()
    return {"status": "success"}


# -----------------------------
# ADMIN: Update DB (RUN PARSER + WAIT)
# -----------------------------
@app.post("/api/admin/update-db")
async def admin_update_db(db: Session = Depends(database.get_db)):
    """
    1) Запускаем локальный парсер shops/ostin_parser.py
    2) Ждём пока он закончит (backend ждёт)
    3) Сбрасываем кэш, чтобы лента показала свежие товары из shops/shop.db
    """
    SHOPS_DIR.mkdir(parents=True, exist_ok=True)

    # shop.db должен существовать — если нет, создадим через SQLAlchemy (таблицы Fit_system)
    models.Base.metadata.create_all(bind=database.engine)

    parser_script = SHOPS_DIR / "ostin_parser.py"
    if not parser_script.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Parser script not found: {parser_script}. Create it (shops/ostin_parser.py).",
        )

    python_bin = sys.executable
    timeout_sec = int(os.getenv("FIT_PARSER_TIMEOUT", "900"))  # 15 мин по умолчанию
    cmd = [python_bin, str(parser_script), "--db", str(SHOP_DB_PATH)]

    logger.info(f"Running parser: {' '.join(cmd)} (timeout={timeout_sec}s)")

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
        logger.error(f"Parser failed rc={proc.returncode} stderr_tail={err_tail}")
        raise HTTPException(
            status_code=500,
            detail=f"Parser failed (rc={proc.returncode}). stderr_tail: {err_tail}",
        )

    invalidate_items_cache()
    count = db.query(models.Garment).count()
    return {
        "status": "ok",
        "db": str(SHOP_DB_PATH),
        "garments_total": count,
        "stdout_tail": out_tail,
        "stderr_tail": err_tail,
    }


# -----------------------------
# ADMIN: MANUAL BUILDER (save real measurements + try-on)
# -----------------------------
def _coerce_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, bool):
            return float(int(x))
        s = str(x).strip().replace(",", ".")
        if s == "":
            return None
        return float(s)
    except Exception:
        return None


@app.post("/api/admin/builder/upsert")
def admin_builder_upsert(payload: Dict[str, Any] = Body(...), db: Session = Depends(database.get_db)):
    """
    Сохраняет/обновляет товар в garments, включая:
    - реальные замеры (metrics[size].real_measurements)
    - примерку (metrics[size].try_on)
    """
    sku = (payload.get("sku") or "").strip()
    if not sku:
        raise HTTPException(status_code=400, detail="sku is required")

    name = (payload.get("name") or "").strip() or sku
    platform = (payload.get("platform") or "ostin").strip()
    image_url = (payload.get("image_url") or "").strip()
    price = _coerce_float(payload.get("price"))

    size_label = (payload.get("size_label") or payload.get("model_size") or "M").strip().upper()
    fit_profile = (payload.get("fit_profile") or "regular").strip().lower()
    fabric = (payload.get("fabric") or "").strip()
    elastane_pct = _coerce_float(payload.get("elastane_pct"))

    # Эти поля ты будешь вносить после магазина:
    real_measurements = payload.get("real_measurements") or {}
    try_on = payload.get("try_on") or {}

    # Можно хранить ещё “служебные” поля (категория/пол/тип)
    internal_category = (payload.get("internal_category") or "").strip()
    gender = (payload.get("gender") or "").strip()
    category_type = (payload.get("category_type") or "").strip()

    # Поддерживаем модельные параметры (если вставляешь из Lamoda текстом)
    model_metrics = payload.get("model_metrics") or {}
    model_size = (payload.get("model_size") or None)

    existing = db.query(models.Garment).filter(models.Garment.sku == sku).first()

    if existing:
        g = existing
    else:
        g = models.Garment(sku=sku)

    g.name = name
    g.platform = platform
    if price is not None:
        g.price = float(price)
    if image_url:
        g.image_url = image_url
    g.in_stock = bool(payload.get("in_stock", True))

    metrics_all = dict(g.metrics or {})
    metrics_all.setdefault(size_label, {})
    size_block = dict(metrics_all.get(size_label) or {})

    # обновляем блок размера
    if fit_profile:
        size_block["fit_profile"] = fit_profile
    if fabric:
        size_block["fabric"] = fabric
    if elastane_pct is not None:
        size_block["elastane_pct"] = float(elastane_pct)
    if internal_category:
        size_block["internal_category"] = internal_category
    if gender:
        size_block["gender"] = gender
    if category_type:
        size_block["category_type"] = category_type

    if model_size:
        size_block["model_size"] = model_size
    if model_metrics:
        size_block["model_metrics"] = model_metrics

    # ключевое: реальные замеры + примерка
    if isinstance(real_measurements, dict) and real_measurements:
        size_block["real_measurements"] = real_measurements
    if isinstance(try_on, dict) and try_on:
        size_block["try_on"] = try_on

    metrics_all[size_label] = size_block
    g.metrics = metrics_all

    db.add(g)
    db.commit()
    db.refresh(g)

    invalidate_items_cache()
    return {"ok": True, "action": "updated" if existing else "created", "sku": sku, "id": g.id, "size": size_label}


@app.get("/api/admin/builder/list")
def admin_builder_list(limit: int = 50, db: Session = Depends(database.get_db)):
    lim = max(1, min(int(limit or 50), 200))
    items = db.query(models.Garment).order_by(models.Garment.id.desc()).limit(lim).all()
    return {"items": items}


@app.get("/api/admin/builder/analysis")
def admin_builder_analysis(db: Session = Depends(database.get_db)):
    """
    Простая аналитика по введённым примеркам:
    считает сколько size-блоков имеют try_on, и сколько отмечено ideal_for_me=true
    """
    garments = db.query(models.Garment).all()

    total_tryons = 0
    total_ideal = 0
    by_category: Dict[str, Dict[str, int]] = {}

    for g in garments:
        if not g.metrics:
            continue
        for size_label, block in (g.metrics or {}).items():
            if not isinstance(block, dict):
                continue
            try_on = block.get("try_on")
            if not isinstance(try_on, dict) or not try_on:
                continue

            total_tryons += 1
            ideal = bool(try_on.get("ideal_for_me"))
            if ideal:
                total_ideal += 1

            cat = (block.get("internal_category") or block.get("category_type") or "unknown").strip() or "unknown"
            by_category.setdefault(cat, {"tryons": 0, "ideal": 0})
            by_category[cat]["tryons"] += 1
            if ideal:
                by_category[cat]["ideal"] += 1

    return {
        "tryons_total": total_tryons,
        "ideal_total": total_ideal,
        "by_category": by_category,
    }


# -----------------------------
# ADMIN: helpers
# -----------------------------
@app.get("/api/admin/stats")
def admin_stats(db: Session = Depends(database.get_db)):
    garments = db.query(models.Garment).count()
    profiles = db.query(models.BodyProfile).count()
    feedback = db.query(models.Feedback).count()
    priors = db.query(models.Prior).count()

    db_path = getattr(database, "DB_PATH", None)
    db_size = None
    if db_path and os.path.exists(db_path):
        db_size = os.path.getsize(db_path)

    return {
        "counts": {"garments": garments, "profiles": profiles, "feedback": feedback, "priors": priors},
        "db": {"path": db_path, "size_bytes": db_size},
    }


@app.get("/api/admin/tables")
def admin_tables(db: Session = Depends(database.get_db)):
    engine = db.get_bind()
    insp = inspect(engine)
    names = [n for n in insp.get_table_names()]
    out = []
    for name in names:
        try:
            cnt = db.execute(text(f"SELECT COUNT(*) AS c FROM {name}")).scalar()
            out.append({"name": name, "rows": int(cnt or 0)})
        except Exception:
            out.append({"name": name, "rows": None})
    out.sort(key=lambda x: (x["name"] or ""))
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


@app.get("/api/admin/garments")
def admin_garments(search: str = "", limit: int = 50, db: Session = Depends(database.get_db)):
    lim = max(1, min(int(limit or 50), 200))
    q = db.query(models.Garment)
    if search:
        s = f"%{search.strip()}%"
        q = q.filter(
            (models.Garment.sku.ilike(s)) | (models.Garment.name.ilike(s)) | (models.Garment.platform.ilike(s))
        )
    items = q.order_by(models.Garment.id.desc()).limit(lim).all()
    return {"items": items}


@app.get("/api/admin/feedback")
def admin_feedback(limit: int = 100, db: Session = Depends(database.get_db)):
    lim = max(1, min(int(limit or 100), 500))
    q = db.query(models.Feedback).order_by(models.Feedback.id.desc()).limit(lim).all()
    return {"items": q}


# -----------------------------
# FRONTEND (static + pages)
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


# Ручной сборщик (если файлы добавлены)
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





