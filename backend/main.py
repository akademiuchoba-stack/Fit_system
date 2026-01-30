from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sys
import os
from sqlalchemy.orm import Session

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import database
import algorithm

app = FastAPI(title="Fit_system API - Production")

# Разрешаем фронтенду обращаться к бэкенду
# В продакшене следует ограничить origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Схемы Pydantic
class UserMetrics(BaseModel):
    gender: str
    height: float
    chest: float
    waist: float
    hips: float
    armLength: float
    inseam: float

class ProductOut(BaseModel):
    sku: str
    name: str
    image_url: str
    category: str
    in_stock: bool

class MatchResponse(BaseModel):
    product: dict
    verdict: dict

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup():
    database.init_db()
    # Сидирование базы данных если она пуста
    db = database.SessionLocal()
    if db.query(database.Product).count() == 0:
        test_products = [
            {
                "sku": "OST-10234-WH",
                "name": "Рубашка Slim Fit (Хлопок)",
                "image_url": "https://picsum.photos/seed/shirt1/400/500",
                "category": "верх",
                "garment_chest": 104.0,
                "garment_waist": 98.0,
                "garment_hips": 106.0,
                "garment_length": 74.0,
                "sleeve_length": 64.0,
                "inseam": 0.0,
                "elasticity_percent": 2.0
            },
            {
                "sku": "OST-88921-DN",
                "name": "Джинсы Regular (Denim)",
                "image_url": "https://picsum.photos/seed/jeans1/400/500",
                "category": "низ",
                "garment_chest": 0.0,
                "garment_waist": 92.0,
                "garment_hips": 108.0,
                "garment_length": 105.0,
                "sleeve_length": 0.0,
                "inseam": 82.0,
                "elasticity_percent": 5.0
            },
            {
                "sku": "OST-44512-TS",
                "name": "Футболка Heavy Oversize",
                "image_url": "https://picsum.photos/seed/tshirt2/400/500",
                "category": "верх",
                "garment_chest": 122.0,
                "garment_waist": 120.0,
                "garment_hips": 122.0,
                "garment_length": 76.0,
                "sleeve_length": 24.0,
                "inseam": 0.0,
                "elasticity_percent": 0.0
            }
        ]
        for p_data in test_products:
            product = database.Product(**p_data)
            db.add(product)
        db.commit()
    db.close()

@app.get("/health")
def health():
    return {"status": "online", "message": "Fit_system is ready"}

@app.post("/api/search", response_model=List[MatchResponse])
def search_and_match(user: UserMetrics, db: Session = Depends(get_db)):
    """
    Основной эндпоинт: получает параметры пользователя, 
    прогоняет их через базу товаров и возвращает вердикты.
    """
    products = db.query(database.Product).filter(database.Product.in_stock == True).all()
    results = []
    
    user_dict = user.dict()
    
    for product in products:
        p_dict = {
            "sku": product.sku,
            "name": product.name,
            "category": product.category,
            "garment_chest": product.garment_chest,
            "garment_waist": product.garment_waist,
            "garment_hips": product.garment_hips,
            "elasticity_percent": product.elasticity_percent,
            "sleeve_length": product.sleeve_length,
            "inseam": product.inseam
        }
        
        verdict = algorithm.calculate_fit_verdict(user_dict, p_dict)
        
        results.append({
            "product": {
                "sku": product.sku,
                "name": product.name,
                "image_url": product.image_url,
                "category": product.category,
                "in_stock": product.in_stock
            },
            "verdict": verdict
        })
    
    # Сортировка по скору (лучшие сверху)
    results.sort(key=lambda x: x["verdict"]["score"], reverse=True)
    return results
