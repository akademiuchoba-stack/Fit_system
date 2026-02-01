from fastapi import FastAPI, Depends, Body, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import subprocess
import datetime

# Импорт из нашего файла database.py
from database import SessionLocal, Product, MeasurementTest, engine, Base

# Принудительное создание таблиц
Base.metadata.create_all(bind=engine)

app = FastAPI()

DEPLOY_SECRET = "super_fit_secret"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_PATH = os.path.join(BASE_DIR, "frontend")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- АЛГОРИТМ РАСЧЕТА ---
def calculate_match(u, p):
    results = {}
    score = 5
    # Минимальные припуски
    MIN_E = {"chest": 4, "waist": 2, "hips": 4}
    
    # Расчет по груди (для верха)
    if p.category == "верх" and p.garment_chest:
        ease = p.garment_chest - u.get('chest', 0)
        if ease < MIN_E['chest']: results['chest'], score = "Туго", score - 2
        elif ease > 15: results['chest'], score = "Оверсайз", score - 1
        else: results['chest'] = "Идеально"

    # Расчет по талии
    if p.garment_waist:
        w_ease = p.garment_waist - u.get('waist', 0)
        if w_ease < MIN_E['waist']: results['waist'], score = "Туго", score - 2
        else: results['waist'] = "ОК"

    return {"details": results, "score": max(0, score)}

# --- API ---

@app.get("/api/status")
async def get_status():
    return {"status": "online"}

@app.get("/api/products")
async def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()

@app.post("/api/match")
async def match_products(params: dict = Body(...), db: Session = Depends(get_db)):
    products = db.query(Product).all()
    recommendations = []
    for p in products:
        analysis = calculate_match(params, p)
        recommendations.append({
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "category": p.category,
            "score": analysis['score'],
            "details": analysis['details'],
            "parsed_data": {"chest": p.garment_chest, "waist": p.garment_waist}
        })
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    return recommendations

@app.post("/api/save-test")
async def save_test(data: dict = Body(...), db: Session = Depends(get_db)):
    try:
        new_test = MeasurementTest(
            user_name=data.get('user_name', 'User'),
            product_id=data['product_id'],
            user_chest=data['user_chest'],
            user_waist=data['user_waist'],
            real_garment_chest=data['real_chest'],
            real_garment_waist=data['real_waist'],
            fit_chest=data['fit_chest'],
            fit_waist=data['fit_waist'],
            conclusion=data['conclusion']
        )
        db.add(new_test)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/stats")
async def get_stats(db: Session = Depends(get_db)):
    tests = db.query(MeasurementTest).all()
    result = []
    for t in tests:
        prod = db.query(Product).filter(Product.id == t.product_id).first()
        result.append({
            "date": t.timestamp.strftime("%d.%m %H:%M"),
            "user": t.user_name,
            "product": prod.name if prod else "N/A",
            "real": f"Г:{t.real_garment_chest} Т:{t.real_garment_waist}",
            "fit": f"Г:{'✓' if t.fit_chest else '✗'} Т:{'✓' if t.fit_waist else '✗'}",
            "note": t.conclusion
        })
    return result

@app.post("/api/webhook-deploy")
async def github_webhook(x_hub_signature_256: str = Header(None)):
    subprocess.run(["git", "-C", BASE_DIR, "pull", "origin", "main"], check=True)
    subprocess.run(["pm2", "restart", "fit_backend"], check=True)
    return {"status": "ok"}

app.mount("/static", StaticFiles(directory=FRONTEND_PATH), name="static")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(FRONTEND_PATH, "index.html"))