import requests
from bs4 import BeautifulSoup
from database import SessionLocal, Product

def add_test_products():
    db = SessionLocal()
    
    # Мы имитируем данные, которые парсер достанет с Lamoda/O'stin
    # В реальном сценарии здесь будет цикл по страницам сайта
    test_data = [
        {
            "sku": "OST-123-RED",
            "name": "Рубашка в клетку O'stin",
            "image_url": "https://images.ostin.com/example1.jpg",
            "category": "верх",
            "in_stock": True,
            "garment_chest": 104.0, # Замер изделия в см
            "garment_waist": 100.0,
            "garment_hips": 102.0,
            "elasticity_percent": 2.0  # 2% эластана
        },
        {
            "sku": "OST-456-BLUE",
            "name": "Джинсы Slim Fit",
            "image_url": "https://images.ostin.com/example2.jpg",
            "category": "низ",
            "in_stock": True,
            "garment_chest": None,
            "garment_waist": 86.0,
            "garment_hips": 98.0,
            "elasticity_percent": 5.0  # Тянутся хорошо
        }
    ]

    for item in test_data:
        # Проверяем, нет ли уже такого товара в базе
        existing_product = db.query(Product).filter(Product.sku == item["sku"]).first()
        if not existing_product:
            new_prod = Product(**item)
            db.add(new_prod)
            print(f"Добавлен товар: {item['name']}")
        else:
            print(f"Товар {item['sku']} уже есть в базе")
    
    db.commit()
    db.close()

if __name__ == "__main__":
    print("Запуск наполнения базы данных...")
    add_test_products()
    print("Готово!")