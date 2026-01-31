from database import SessionLocal, Product

def seed_data():
    db = SessionLocal()
    # Очистим старые тестовые данные, если они есть
    db.query(Product).delete()
    
    products = [
        {
            "sku": "OST-SHIRT-001",
            "name": "Рубашка Slim Fit O'stin",
            "image_url": "https://ostin.com/upload/shirt.jpg",
            "category": "верх",
            "in_stock": True,
            "garment_chest": 102.0,  # Замер изделия в груди
            "garment_waist": 96.0,   # Замер в талии
            "garment_hips": 100.0,
            "elasticity_percent": 2.0 # Немного тянется
        },
        {
            "sku": "OST-PANTS-002",
            "name": "Брюки Chino O'stin",
            "image_url": "https://ostin.com/upload/pants.jpg",
            "category": "низ",
            "in_stock": True,
            "garment_chest": None,
            "garment_waist": 88.0,
            "garment_hips": 104.0,
            "elasticity_percent": 5.0 # Хорошо тянутся
        }
    ]

    for p in products:
        db.add(Product(**p))
    
    db.commit()
    db.close()
    print("База данных наполнена товарами O'stin (Ангарск)")

if __name__ == "__main__":
    seed_data()