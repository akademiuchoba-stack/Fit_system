import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# 1) Определяем корень проекта (на один уровень выше папки backend)
# __file__ = /root/Fit_system/backend/database.py
# BASE_DIR = /root/Fit_system/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOPS_DIR = os.path.join(BASE_DIR, "shops")

# 2) Создаем папку shops, если её нет
os.makedirs(SHOPS_DIR, exist_ok=True)

# 3) Путь к БД
DB_PATH = os.path.join(SHOPS_DIR, "shop.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# 4) Инициализация Engine (SQLite)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
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

# -----------------------------
# "Автомиграции" для SQLite
# (чтобы ничего не ломалось на старой базе)
# -----------------------------
def _sqlite_column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == column for r in rows)  # r[1] = column name

def _sqlite_table_exists(conn, table: str) -> bool:
    row = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
        {"t": table},
    ).fetchone()
    return row is not None

def _ensure_sqlite_column(conn, table: str, column: str, ddl_type: str):
    # Примечание: ALTER TABLE ADD COLUMN в SQLite безопасен:
    # - не трогает существующие данные
    # - добавляет NULL в старые строки
    if not _sqlite_table_exists(conn, table):
        return
    if _sqlite_column_exists(conn, table, column):
        return
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
    conn.commit()

def init_db(BaseModel) -> None:
    """Создать таблицы и добавить недостающие колонки в старой базе."""
    # 1) создаём таблицы по ORM (если их не было)
    BaseModel.metadata.create_all(bind=engine)

    # 2) "легкая миграция" — добавляем то, что могло появиться позже
    # Сейчас нам нужно только: body_profiles.height (рост)
    with engine.connect() as conn:
        _ensure_sqlite_column(conn, "body_profiles", "height", "FLOAT")

