
import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Определяем корень проекта (на один уровень выше папки backend)
# __file__ = /root/Fit_system/backend/database.py
# BASE_DIR = /root/Fit_system/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOPS_DIR = os.path.join(BASE_DIR, "shops")

# 2. Создаем папку shops, если её нет
if not os.path.exists(SHOPS_DIR):
    try:
        os.makedirs(SHOPS_DIR, exist_ok=True)
        print(f"📁 Created directory: {SHOPS_DIR}")
    except Exception as e:
        print(f"❌ Error creating directory {SHOPS_DIR}: {e}")

# 3. Путь к БД
DB_PATH = os.path.join(SHOPS_DIR, "shop.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# 4. Инициализация Engine с поддержкой WAL для MVP
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# Включение режима WAL для SQLite (улучшает параллелизм)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA temp_store=MEMORY")
    # cache_size отрицательное = килобайты; ~20MB
    cursor.execute("PRAGMA cache_size=-20000")
    # mmap ускоряет чтение, если ОС позволяет
    try:
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
    except Exception:
        pass
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
