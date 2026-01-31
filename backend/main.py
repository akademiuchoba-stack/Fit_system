from fastapi import FastAPI, Depends, Body, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import subprocess

# Импортируем настройки базы из нашего соседнего файла database.py
from database import SessionLocal, Product

app = FastAPI(title="Идеальный Припуск API")

# Секретное слово для деплоя (укажи его в настройках Webhook на GitHub)
DEPLOY_SECRET = "super_fit_secret"

# Настройка путей
# Файл лежит в /backend, значит frontend на один уровень выше
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_PATH = os.path.join(BASE_DIR, "frontend")

# Подключение к базе данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ЛОГИКА АЛГОРИТМА «ИДЕАЛЬНЫЙ ПРИПУСК» ---
def calculate_match(user_params, product):
    results = {}
    total_score = 5
    
    # Константы технического припуска (Wearing Ease) по ГОСТ/стандартам
    # chest: 4см, waist: 2см, hips: 4см
    MIN_EASE = {"chest": 4, "waist": 2, "hips": 4}
    
    # 1. Проверка зоны ГРУДИ (только для категории "верх")
    if product.category == "верх" and product.garment_chest:
        actual_ease = product.garment_chest - user_params.get('chest', 0)
        
        # Учет эластичности: если эластан > 3%, допускаем меньший припуск
        stretch_bonus = 0
        if product.elasticity_percent and product.elasticity_percent > 3:
            stretch_bonus = product.elasticity_percent * 0.5
            
        effective_ease = actual_ease + stretch_bonus

        if effective_ease < MIN_EASE['chest']:
            results['chest'] = "Туго"
            total_score -= 2
        elif effective_ease > 15:
            results['chest'] = "Велико (Оверсайз)"
            total_score -= 1
        else:
            results['chest'] = "Идеально"

    # 2. Проверка ТАЛИИ
    if product.garment_waist:
        actual_waist_ease = product.garment_waist - user_params.get('waist', 0)
        if actual_waist_ease < MIN_EASE['waist']:
            results['waist'] = "Туго в талии"
            total_score -= 2
        else:
            results['waist'] = "ОК"

    # 3. Проверка БЕДЕР
    if product.garment_hips:
        actual_hips_ease = product.garment_hips - user_params.get('hips', 0)
        if actual_hips_ease < MIN_EASE['hips']:
            results['hips'] = "Узко в бедрах"
            total_score -= 2
        else:
            results['hips'] = "ОК"

    return {"details": results, "score": max(0, total_score)}

# --- API ЭНДПОИНТЫ ---

@app.get("/api/status")
async def get_status():
    """Проверка работы сервера"""
    return {"status": "online", "message": "Система Идеальный Припуск готова к работе!"}

@app.get("/api/products")
async def list_products(db: Session = Depends(get_db)):
    """Вывод всех товаров в наличии"""
    return db.query(Product).filter(Product.in_stock == True).all()

@app.post("/api/match")
async def match_products(params: dict = Body(...), db: Session = Depends(get_db)):
    """Основной расчет подбора"""
    products = db.query(Product).filter(Product.in_stock == True).all()
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
            "image": p.image_url
        })
    
    # Сортировка: сначала лучшие ( score 5 )
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    return recommendations

@app.post("/api/webhook-deploy")
async def github_webhook(x_hub_signature_256: str = Header(None)):
    """Автоматический деплой при пуше в GitHub"""
    try:
        # 1. Скачиваем новый код
        subprocess.run(["git", "-C", BASE_DIR, "pull", "origin", "main"], check=True)
        # 2. Перезапускаем сам процесс сервера через PM2
        # (Процесс должен называться 'fit_backend')
        subprocess.run(["pm2", "restart", "fit_backend"], check=True)
        return {"status": "success", "message": "Код обновлен, сервер перезагружен"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- РАЗДАЧА ФРОНТЕНДА ---

# Раздаем папку frontend как статику
app.mount("/static", StaticFiles(directory=FRONTEND_PATH), name="static")

@app.get("/")
async def read_index():
    """Главная страница приложения"""
    return FileResponse(os.path.join(FRONTEND_PATH, "index.html"))