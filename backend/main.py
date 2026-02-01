from fastapi import FastAPI, Depends, Body, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import subprocess
import datetime

# Импорт из нашего файла database.py
from database import SessionLocal, Product, MeasurementTest, engine, Base

# Создаем таблицы, если их еще нет
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EComp: Smart Shopping System")

DEPLOY_SECRET = "super_fit_secret"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_PATH = os.path.join(BASE_DIR, "frontend")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- ЛОГИКА АЛГОРИТМА «ИДЕАЛЬНЫЙ ПРИПУСК» ---
def calculate_match(user_params, product):
    results = {}
    total_score = 5
    # Технические припуски (Wearing Ease)
    MIN_EASE = {"chest": 4, "waist": 2, "hips": 4}
    
    # Расчет по груди
    if product.category == "верх" and product.garment_chest:
        actual_ease = product.garment_chest - user_params.get('chest', 0)
        stretch_bonus = (product.elasticity_percent * 0.5) if product.elasticity_percent > 3 else 0
        effective_ease = actual_ease + stretch_bonus
        if effective_ease < MIN_EASE['chest']:
            results['chest'] = "Туго"
            total_score -= 2
        elif effective_ease > 15:
            results['chest'] = "Оверсайз"
            total_score -= 1
        else: results['chest'] = "Идеально"

    # Расчет по талии
    if product.garment_waist:
        actual_waist_ease = product.garment_waist - user_params.get('waist', 0)
        if actual_waist_ease < MIN_EASE['waist']:
            results['waist'] = "Туго"
            total_score -= 2
        else: results['waist'] = "ОК"

    return {"details": results, "score": max(0, total_score)}

# --- API ЭНДПОИНТЫ ---

@app.get("/api/status")
async def get_status():
    return {"status": "online", "message": "Система EComp готова"}

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
            # Данные парсинга для сравнения
            "parsed_data": {
                "chest": p.garment_chest,
                "waist": p.garment_waist,
                "hips": p.garment_hips
            }
        })
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    return recommendations

@app.post("/api/save-test")
async def save_test(data: dict = Body(...), db: Session = Depends(get_db)):
    """Сохранение статистики замера в магазине"""
    try:
        new_test = MeasurementTest(
            user_name=data.get('user_name', 'Default User'),
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
    """Получение всей накопленной статистики"""
    tests = db.query(MeasurementTest).all()
    result = []
    for t in tests:
        prod = db.query(Product).filter(Product.id == t.product_id).first()
        result.append({
            "date": t.timestamp.strftime("%Y-%m-%d %H:%M"),
            "user": t.user_name,
            "product": prod.name if prod else "Unknown",
            "real_vs_parsed": f"C:{t.real_garment_chest} W:{t.real_garment_waist}",
            "fit": f"C:{t.fit_chest} W:{t.fit_waist}",
            "conclusion": t.conclusion
        })
    return result

@app.post("/api/webhook-deploy")
async def github_webhook(x_hub_signature_256: str = Header(None)):
    try:
        subprocess.run(["git", "-C", BASE_DIR, "pull", "origin", "main"], check=True)
        subprocess.run(["pm2", "restart", "fit_backend"], check=True)
        return {"status": "deployed"}
    except: return {"status": "error"}

app.mount("/static", StaticFiles(directory=FRONTEND_PATH), name="static")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(FRONTEND_PATH, "index.html"))