
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Определение путей
# Проект находится в /root/Fit_system/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOPS_DIR = os.path.join(BASE_DIR, "shops")

# Автоматическое создание папки для баз данных, если её нет
if not os.path.exists(SHOPS_DIR):
    os.makedirs(SHOPS_DIR)

# Основная база данных магазина
DB_PATH = os.path.join(SHOPS_DIR, "shop.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
