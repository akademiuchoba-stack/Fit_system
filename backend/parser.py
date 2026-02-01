from database import SessionLocal, Product

def seed_data():
    db = SessionLocal()
    db.query(Product).delete()
    
    test_products = [
        {
            "sku": "OST-SH-001", "name": "Рубашка Oxford Slim", "size": "M", "category": "верх",
            "image_url": "https://ostin.com/upload/resize_cache/iblock/c34/400_600_1/c34a2e.jpg",
            "garment_chest": 104.0, "garment_waist": 98.0, "garment_hips": 102.0, "elasticity_percent": 2.0
        },
        {
            "sku": "OST-JN-502", "name": "Джинсы Denim Straight", "size": "32/34", "category": "низ",
            "image_url": "https://ostin.com/upload/resize_cache/iblock/a12/400_600_1/a12b4f.jpg",
            "garment_chest": None, "garment_waist": 86.0, "garment_hips": 104.0, "elasticity_percent": 5.0
        }
    ]
    
    for p in test_products:
        db.add(Product(**p))
    
    db.commit()
    db.close()
    print("База наполнена товарами с ФОТО и РАЗМЕРАМИ!")

if __name__ == "__main__":
    seed_data()