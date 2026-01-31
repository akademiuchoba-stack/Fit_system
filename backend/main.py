from fastapi import FastAPI, Depends, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
from database import SessionLocal, Product

app = FastAPI()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ЛОГИКА АЛГОРИТМА
def calculate_match(user_params, product):
    results = {}
    total_score = 5
    
    # Константы технического припуска (Wearing Ease)
    E_w = {"chest": 4, "waist": 2, "hips": 4}
    
    # 1. Проверка по груди (если это верх)
    if product.category == "верх" and product.garment_chest:
        actual_ease = product.garment_chest - user_params['chest']
        # Учет эластичности (Stretch Factor)
        if product.elasticity_percent > 3:
            effective_ease = actual_ease + (product.elasticity_percent * 0.5)
        else:
            effective_ease = actual_ease

        if effective_ease < E_w['chest']:
            results['chest'] = "Туго"
            total_score -= 2
        elif effective_ease > 12:
            results['chest'] = "Велико (Оверсайз)"
            total_score -= 1
        else:
            results['chest'] = "Идеально"

    # 2. Проверка по талии
    if product.garment_waist:
        actual_ease = product.garment_waist - user_params['waist']
        if actual_ease < E_w['waist']:
            results['waist'] = "Туго в талии"
            total_score -= 2
        else:
            results['waist'] = "ОК"

    return {"verdict": results, "score": max(0, total_score)}

@app.post("/api/match")
async def match_products(params: dict = Body(...), db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.in_stock == True).all()
    recommendations = []
    
    for p in products:
        analysis = calculate_match(params, p)
        recommendations.append({
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "score": analysis['score'],
            "details": analysis['verdict']
        })
    
    # Сортируем: сначала лучшие совпадения
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    return recommendations

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_PATH = os.path.join(BASE_DIR, "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_PATH), name="static")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(FRONTEND_PATH, "index.html"))