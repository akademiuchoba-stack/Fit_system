import os
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

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
# API ЭНДПОИНТЫ
# -----------------------------
@app.get("/api/items")
def get_items(db: Session = Depends(database.get_db)):
    try:
        items = db.query(models.Garment).filter(models.Garment.in_stock == True).all()
        return items
    except Exception as e:
        logger.error(f"Error fetching items: {e}")
        raise HTTPException(status_code=500, detail="Database error")


@app.post("/api/calculate")
def calculate_for_user(req: models.FitRequest, db: Session = Depends(database.get_db)):
    logger.info(f"Calculating fit for user: {req.user.name}")
    items = db.query(models.Garment).filter(models.Garment.in_stock == True).all()
    results = []
    user_data = req.user.dict()

    for item in items:
        best_size = None
        best_score = -1

        for size_label, m in item.metrics.items():
            fit = logic.calculate_fit(user_data, m)
            if fit['score'] > best_score:
                best_score = fit['score']
                best_size = {
                    "size": size_label,
                    "fit": fit,
                    "item_id": item.id,
                    "sku": item.sku,
                    "name": item.name,
                    "image": item.image_url,
                    "platform": item.platform
                }
        if best_size:
            results.append(best_size)

    results.sort(key=lambda x: x['fit']['score'], reverse=True)
    return results


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
    mock_items = [
        {
            "sku": "OST-99122",
            "name": "Рубашка Oxford Regular",
            "platform": "ostin",
            "image_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&q=80&w=800",
            "metrics": {
                "M": {"chest": 54, "shoulder": 46, "sleeve": 64, "length": 72},
                "L": {"chest": 57, "shoulder": 48, "sleeve": 65, "length": 74}
            }
        },
        {
            "sku": "LAM-77332",
            "name": "Свитшот Premium Cotton",
            "platform": "lamoda",
            "image_url": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&q=80&w=800",
            "metrics": {
                "S": {"chest": 52, "shoulder": 44, "sleeve": 62, "length": 68},
                "M": {"chest": 55, "shoulder": 45, "sleeve": 64, "length": 70}
            }
        },
        {
            "sku": "OST-55411",
            "name": "Куртка демисезонная Loft",
            "platform": "ostin",
            "image_url": "https://images.unsplash.com/photo-1551488831-00ddcb6c6bd3?auto=format&fit=crop&q=80&w=800",
            "metrics": {
                "M": {"chest": 58, "shoulder": 48, "sleeve": 66, "length": 75},
                "L": {"chest": 61, "shoulder": 50, "sleeve": 67, "length": 77}
            }
        }
    ]

    for item_data in mock_items:
        existing = db.query(models.Garment).filter(models.Garment.sku == item_data['sku']).first()
        if not existing:
            new_item = models.Garment(**item_data)
            db.add(new_item)
            db.flush()
            for size, m in item_data['metrics'].items():
                new_prior = models.Prior(
                    garment_id=new_item.id,
                    size_label=size,
                    mu_chest=m['chest'],
                    mu_sleeve=m['sleeve']
                )
                db.add(new_prior)

    db.commit()
    return {"status": "Matrix Updated: 3 SKUs Active in Angarsk (Festival Mall)"}

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
if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
