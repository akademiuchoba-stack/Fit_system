import os
import logging
from pathlib import Path
from time import time

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect

from . import models, database, logic, parser, calibration

# -----------------------------
# ЛОГИРОВАНИЕ
# -----------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -----------------------------
# FASTAPI
# -----------------------------
app = FastAPI(title="Fit_system API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# -----------------------------
# ИНИЦИАЛИЗАЦИЯ БД
# -----------------------------
models.Base.metadata.create_all(bind=database.engine)

# -----------------------------
# КЭШ ТОВАРОВ (ускоряет /api/calculate при повторных запросах)
# -----------------------------
_ITEMS_CACHE = {"ts": 0.0, "items": None}
CACHE_TTL_SEC = int(os.getenv("FIT_ITEMS_CACHE_TTL", "30"))

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
# API ЭНДПОИНТЫ
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
# PROFILES (Кабинет)
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
    # Upsert по имени — так удобнее в магазине
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
        # проверка уникальности имени
        conflict = db.query(models.BodyProfile).filter(models.BodyProfile.name == data["name"], models.BodyProfile.id != profile_id).first()
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


@app.post("/api/calculate")
def calculate_for_profile(
    req: models.CalculateRequest,
    db: Session = Depends(database.get_db),
    limit: int = Query(20, ge=1, le=200),
):
    """
    Возвращает N лучших карточек для выбранного профиля.
    Фронт шлёт: { profile_id: 123 } (см. frontend/index.js).
    """
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
        """
        В БД MVP часто лежат "полуобхваты" (например, грудь 54 см) вместо окружности.
        Чтобы не ломать расчёт, приводим к окружности, если значение похоже на полуобхват.
        """
        mm = dict(m or {})
        for k in ("chest", "waist", "hips"):
            v = mm.get(k)
            try:
                v = float(v)
            except Exception:
                continue
            # эвристика: если пользовательский обхват > 90, а у изделия < 80 — вероятно полуобхват
            u = user_data.get(k)
            if u and u > 90 and v < 80:
                mm[k] = v * 2.0
        # плечи/рукав обычно в длинах → оставляем
        if "shoulder" in mm and "shoulders" not in mm:
            mm["shoulders"] = mm.pop("shoulder")
        return mm

    results = []

    for item in items:
        if not item.metrics:
            continue

        best = None
        best_score = -1.0

        # item.metrics: { "M": {...}, "L": {...} }
        for size_label, raw_metrics in (item.metrics or {}).items():
            m_norm = normalize_item_metrics(raw_metrics or {})
            garment_payload = {
                "id": item.id,
                "sku": item.sku,
                "name": item.name,
                "platform": item.platform,
                "image_url": item.image_url,
                # доп. поля для "идеального припуска" (могут быть пустыми)
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
                    # отдаём "сырые" промеры, чтобы можно было сравнить с "реальными" в магазине
                    "metrics": m_norm,
                }

        if best:
            results.append(best)

    results.sort(key=lambda x: x["fit"]["score"], reverse=True)

    # Небольшая диверсификация (платформы/категории)
    buckets = {}
    for r in results:
        key = (r.get("platform") or "unknown")
        buckets.setdefault(key, []).append(r)

    diversified = []
    keys = list(buckets.keys())
    i = 0
    while len(diversified) < min(limit, len(results)):
        k = keys[i % len(keys)]
        if buckets[k]:
            diversified.append(buckets[k].pop(0))
        keys = [kk for kk in keys if buckets.get(kk)]
        if not keys:
            break
        i += 1

    return diversified[:limit]


@app.post("/api/feedback")
def submit_feedback(fb: models.FeedbackSubmit, db: Session = Depends(database.get_db)):
    logger.info(f"Feedback received for item {fb.garment_id} from {fb.user_id}")
    new_fb = models.Feedback(
        garment_id=fb.garment_id,
        user_id=fb.user_id,
        size_selected=fb.size_selected,
        judgment=fb.judgment,
        real_measurements=fb.real_measurements
    )
    db.add(new_fb)

    if fb.real_measurements:
        garment = db.query(models.Garment).filter(models.Garment.id == fb.garment_id).first()
        prior = db.query(models.Prior).filter(
            models.Prior.garment_id == fb.garment_id,
            models.Prior.size_label == fb.size_selected
        ).first()

        if prior and 'chest' in fb.real_measurements:
            new_mu, new_sigma = calibration.bayesian_update(
                prior.mu_chest, prior.sigma_chest, fb.real_measurements['chest']
            )
            prior.mu_chest = new_mu
            prior.sigma_chest = new_sigma

            updated_metrics = dict(garment.metrics)
            updated_metrics[fb.size_selected]['chest'] = new_mu
            garment.metrics = updated_metrics
            logger.info(f"Bayesian update completed for {garment.sku} size {fb.size_selected}")

    db.commit()
    return {"status": "success"}


@app.post("/api/admin/update-db")
async def update_database(db: Session = Depends(database.get_db)):
    """
    Обновляет локальную БД товаров.

    MVP-режим:
    - если задан env FIT_IMPORT_FILE=/path/to/items.json|jsonl|csv → импортируем оттуда (самый надёжный путь).
    - иначе оставляем демо-товары, чтобы система не была "пустой".

    Формат импорта (JSON/CSV):
      sku, name, platform, image_url, metrics (как JSON), description (опц.)
    """
    import_file = os.getenv("FIT_IMPORT_FILE", "").strip()
    parsed_items = []

    if import_file:
        try:
            parsed_items = parser.load_items_from_local_file(import_file)
            logger.info(f"Imported {len(parsed_items)} items from {import_file}")
        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise HTTPException(status_code=400, detail=f"Import failed: {e}")

        # конвертируем ParsedItem -> dict для унификации
        items_data = []
        for it in parsed_items:
            items_data.append({
                "sku": it.sku,
                "name": it.name,
                "platform": (it.brand or "").lower() or ("lamoda" if "lamoda" in (it.url or "").lower() else (it.category or "").lower() or "unknown"),
                "image_url": it.image_url,
                "metrics": it.metrics or {},
                # доп. поля можно хранить внутри metrics по ключам
            })
    else:
        # Демо, чтобы система была готова к показу
        items_data = [
            {
                "sku": "OST-99122",
                "name": "Рубашка Oxford Regular",
                "platform": "ostin",
                "image_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&q=80&w=800",
                "metrics": {
                    "M": {"chest": 54, "shoulder": 46, "sleeve": 64, "length": 72, "fit_profile": "regular"},
                    "L": {"chest": 57, "shoulder": 48, "sleeve": 65, "length": 74, "fit_profile": "regular"}
                }
            },
            {
                "sku": "LAM-77332",
                "name": "Свитшот Premium Cotton",
                "platform": "lamoda",
                "image_url": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&q=80&w=800",
                "metrics": {
                    "S": {"chest": 52, "shoulder": 44, "sleeve": 62, "length": 68, "fit_profile": "oversize"},
                    "M": {"chest": 55, "shoulder": 45, "sleeve": 64, "length": 70, "fit_profile": "oversize"}
                }
            },
            {
                "sku": "OST-55411",
                "name": "Куртка демисезонная Loft",
                "platform": "ostin",
                "image_url": "https://images.unsplash.com/photo-1551488831-00ddcb6c6bd3?auto=format&fit=crop&q=80&w=800",
                "metrics": {
                    "M": {"chest": 58, "shoulder": 48, "sleeve": 66, "length": 75, "fit_profile": "regular"},
                    "L": {"chest": 61, "shoulder": 50, "sleeve": 67, "length": 77, "fit_profile": "regular"}
                }
            }
        ]

    # Upsert garments + priors
    for item_data in items_data:
        sku = item_data.get("sku")
        if not sku:
            continue
        existing = db.query(models.Garment).filter(models.Garment.sku == sku).first()
        if not existing:
            existing = models.Garment(
                sku=sku,
                name=item_data.get("name") or sku,
                platform=item_data.get("platform") or "unknown",
                image_url=item_data.get("image_url"),
                metrics=item_data.get("metrics") or {},
                in_stock=True,
            )
            db.add(existing)
            db.flush()
        else:
            existing.name = item_data.get("name") or existing.name
            existing.platform = item_data.get("platform") or existing.platform
            existing.image_url = item_data.get("image_url") or existing.image_url
            existing.metrics = item_data.get("metrics") or existing.metrics
            existing.in_stock = True

        # Priors (для калибровки)
        # В MVP создаём по одному prior на size_label, если не создан.
        for size_label, m in (existing.metrics or {}).items():
            if not isinstance(m, dict):
                continue
            prior = db.query(models.Prior).filter(
                models.Prior.garment_id == existing.id,
                models.Prior.size_label == str(size_label),
            ).first()
            if prior:
                continue
            mu_chest = float(m.get("chest", 0) or 0)
            mu_sleeve = float(m.get("sleeve", 0) or 0)
            prior = models.Prior(
                garment_id=existing.id,
                size_label=str(size_label),
                mu_chest=mu_chest,
                sigma_chest=4.0,   # стартовая неопределённость
                mu_sleeve=mu_sleeve,
                sigma_sleeve=2.0,
            )
            db.add(prior)

    db.commit()
    invalidate_items_cache()
    return {"status": "DB updated", "import_file": import_file or None, "count": len(items_data)}


@app.get("/api/admin/stats")
def admin_stats(db: Session = Depends(database.get_db)):
    try:
        garments = db.query(models.Garment).count()
        profiles = db.query(models.BodyProfile).count()
        feedback = db.query(models.Feedback).count()
        priors = db.query(models.Prior).count()

        last_feedback = (
            db.query(models.Feedback)
            .order_by(models.Feedback.id.desc())
            .limit(30)
            .all()
        )

        db_path = getattr(database, "DB_PATH", None)
        db_size = None
        if db_path and os.path.exists(db_path):
            db_size = os.path.getsize(db_path)

        return {
            "counts": {
                "garments": garments,
                "profiles": profiles,
                "feedback": feedback,
                "priors": priors,
            },
            "db": {
                "path": db_path,
                "size_bytes": db_size,
            },
            "recent_feedback": [
                {
                    "id": f.id,
                    "garment_id": f.garment_id,
                    "user_id": f.user_id,
                    "size_selected": f.size_selected,
                    "judgment": f.judgment,
                    "real_measurements": f.real_measurements,
                }
                for f in last_feedback
            ],
        }
    except Exception as e:
        logger.error(f"admin stats error: {e}")
        raise HTTPException(status_code=500, detail="Stats error")

# -----------------------------
# FRONTEND
# -----------------------------
@app.get("/")
async def read_index():
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)
    raise HTTPException(status_code=404, detail="Frontend index.html not found")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# -----------------------------
# LOCAL RUN
# -----------------------------

# -------------------------
# Admin API (read-only helpers)
# -------------------------

@app.get("/api/admin/tables")
def admin_tables(db: Session = Depends(get_db)):
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
def admin_table_preview(table_name: str, limit: int = 50, db: Session = Depends(get_db)):
    engine = db.get_bind()
    insp = inspect(engine)
    allowed = set(insp.get_table_names())
    if table_name not in allowed:
        raise HTTPException(status_code=404, detail="Unknown table")
    lim = max(1, min(int(limit or 50), 200))
    rows = db.execute(text(f"SELECT * FROM {table_name} LIMIT :lim"), {"lim": lim}).mappings().all()
    return {"rows": [dict(r) for r in rows]}

@app.get("/api/admin/garments")
def admin_garments(search: str = "", limit: int = 50, db: Session = Depends(get_db)):
    lim = max(1, min(int(limit or 50), 200))
    q = db.query(models.Garment)
    if search:
        s = f"%{search.strip()}%"
        q = q.filter(
            (models.Garment.sku.ilike(s)) |
            (models.Garment.name.ilike(s)) |
            (models.Garment.platform.ilike(s))
        )
    items = q.order_by(models.Garment.id.desc()).limit(lim).all()
    out = []
    for g in items:
        out.append({
            "id": g.id,
            "platform": g.platform,
            "sku": g.sku,
            "name": g.name,
            "in_stock": bool(g.in_stock),
            "image_url": g.image_url,
            "sizes": ",".join(list((g.size_metrics or {}).keys())) if isinstance(g.size_metrics, dict) else None,
            "updated_at": getattr(g, "updated_at", None),
        })
    return {"items": out}

@app.get("/api/admin/feedback")
def admin_feedback(limit: int = 100, db: Session = Depends(get_db)):
    lim = max(1, min(int(limit or 100), 500))
    q = db.query(models.Feedback).order_by(models.Feedback.id.desc()).limit(lim).all()
    profile_by_id = {p.id: p for p in db.query(models.BodyProfile).all()} if hasattr(models, "BodyProfile") else {}
    garment_by_id = {g.id: g for g in db.query(models.Garment).all()}
    out = []
    for f in q:
        out.append({
            "id": f.id,
            "profile": getattr(profile_by_id.get(getattr(f, "user_id", None), None), "name", None),
            "garment": getattr(garment_by_id.get(getattr(f, "garment_id", None), None), "name", None),
            "garment_sku": getattr(garment_by_id.get(getattr(f, "garment_id", None), None), "sku", None),
            "size_selected": getattr(f, "size_selected", None),
            "created_at": getattr(f, "created_at", None),
            "payload": getattr(f, "payload", None),
        })
    return {"items": out}


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
