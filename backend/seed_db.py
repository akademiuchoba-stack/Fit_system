
import os
import sys
import json
from sqlalchemy.orm import Session

# Добавляем корень проекта в путь, чтобы работали импорты из backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import models, database

def seed_data():
    """Инициализация базы данных и наполнение тестовой матрицей для ТРЦ Фестиваль."""
    print("🚀 Fit_system: Start Database Initialization...")
    
    # Убеждаемся, что папка существует перед созданием таблиц
    if not os.path.exists(database.SHOPS_DIR):
        os.makedirs(database.SHOPS_DIR, exist_ok=True)
    
    # Создаем/Обновляем структуру таблиц
    print("🏗 Building schema in shops/shop.db...")
    models.Base.metadata.create_all(bind=database.engine)
    
    db = database.SessionLocal()
    
    # Проверка на дубликаты перед наполнением
    if db.query(models.Garment).count() > 0:
        print("⚠️ Database already contains data. Skipping seed to prevent duplicates.")
        db.close()
        return

    print("🧪 Injecting Test Garment Matrix (Angarsk Edition)...")
    
    items = [
        {
            "sku": "OST-OX-001",
            "name": "Рубашка Oxford Regular Fit",
            "platform": "ostin",
            "price": 2499.0,
            "image_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&q=80&w=800",
            "metrics": {
                "M": {"chest": 54, "shoulder": 46, "sleeve": 64, "length": 72},
                "L": {"chest": 57, "shoulder": 48, "sleeve": 65, "length": 74},
                "XL": {"chest": 60, "shoulder": 50, "sleeve": 66, "length": 76}
            }
        },
        {
            "sku": "LAM-SW-772",
            "name": "Свитшот Premium Cotton Navy",
            "platform": "lamoda",
            "price": 4200.0,
            "image_url": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&q=80&w=800",
            "metrics": {
                "S": {"chest": 52, "shoulder": 44, "sleeve": 62, "length": 68},
                "M": {"chest": 55, "shoulder": 45, "sleeve": 64, "length": 70}
            }
        },
        {
            "sku": "OST-JK-554",
            "name": "Куртка-бомбер Loft Tech",
            "platform": "ostin",
            "price": 5999.0,
            "image_url": "https://images.unsplash.com/photo-1551488831-00ddcb6c6bd3?auto=format&fit=crop&q=80&w=800",
            "metrics": {
                "M": {"chest": 58, "shoulder": 48, "sleeve": 66, "length": 75},
                "L": {"chest": 61, "shoulder": 50, "sleeve": 67, "length": 77},
                "XL": {"chest": 64, "shoulder": 52, "sleeve": 68, "length": 79}
            }
        }
    ]

    try:
        for item_data in items:
            garment = models.Garment(**item_data)
            db.add(garment)
            db.flush() # Получаем ID для Priors
            
            # Создаем начальные байесовские априорные распределения (Priors)
            for size_label, m in item_data['metrics'].items():
                prior = models.Prior(
                    garment_id=garment.id,
                    size_label=size_label,
                    mu_chest=m.get('chest', 0),
                    sigma_chest=1.2,
                    mu_sleeve=m.get('sleeve', 0),
                    sigma_sleeve=1.0
                )
                db.add(prior)

        db.commit()
        print("✅ Database successfully initialized in shops/shop.db")
    except Exception as e:
        db.rollback()
        print(f"❌ Error during seeding: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
