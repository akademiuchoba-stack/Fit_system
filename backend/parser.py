from database import SessionLocal, Product

def seed_data():
    db = SessionLocal()
    db.query(Product).delete()
    
    test_products = [
        {
            "sku": "OST-SH-001", "name": "Рубашка O'stin Regular", "category": "верх",
            "image_url": "https://ostin.com/1.jpg",
            "garment_chest": 108.0, "garment_waist": 104.0, "garment_hips": 106.0,
            "garment_shoulders": 46.0, "garment_sleeve": 66.0, "garment_height": 182.0
        },
        {
            "sku": "OST-JN-002", "name": "Джинсы O'stin Slim", "category": "низ",
            "image_url": "https://ostin.com/2.jpg",
            "garment_chest": None, "garment_waist": 88.0, "garment_hips": 102.0,
            "garment_shoulders": None, "garment_sleeve": None, "garment_height": 110.0
        }
    ]
    
    for p in test_products:
        db.add(Product(**p))
    
    db.commit()
    db.close()
    print("База успешно наполнена 6-параметрическими товарами!")

if __name__ == "__main__":
    seed_data()