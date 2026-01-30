
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sys
import os

# Добавляем текущую директорию в путь, чтобы видеть соседние файлы
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import database
import algorithm

app = FastAPI(title="Fit_system API - Production")

# Разрешаем фронтенду обращаться к бэкенду
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserMetrics(BaseModel):
    gender: str
    height: float
    chest: float
    waist: float
    hips: float
    armLength: float
    inseam: float

class ProductIn(BaseModel):
    sku: str
    garment_chest: float
    garment_waist: float
    garment_hips: float
    category: str
    elasticity_percent: float

@app.on_event("startup")
def startup():
    # Создаем базу данных при запуске
    database.init_db()

@app.get("/health")
def health():
    return {"status": "online", "message": "Fit_system is ready"}

@app.post("/api/match")
def match_product(user: UserMetrics, product: ProductIn):
    """
    Безопасный расчет. Формулы скрыты в algorithm.py
    """
    try:
        verdict = algorithm.calculate_fit_verdict(user.dict(), product.dict())
        return verdict
    except Exception as e:
        print(f"Error in calculation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error during calculation")
