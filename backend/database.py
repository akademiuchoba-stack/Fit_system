import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Определяем путь к базе данных так, чтобы он работал и на ПК, и на сервере
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'shop.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    name = Column(String)
    category = Column(String)
    image_url = Column(String)
    in_stock = Column(Boolean, default=True)
    
    garment_chest = Column(Float)
    garment_waist = Column(Float)
    garment_hips = Column(Float)
    garment_length = Column(Float)
    sleeve_length = Column(Float)
    inseam = Column(Float)
    
    elasticity_percent = Column(Float, default=0)
    
    model_height = Column(Float)
    model_chest = Column(Float)
    model_waist = Column(Float)
    model_hips = Column(Float)
    size_on_model = Column(String)

def init_db():
    Base.metadata.create_all(bind=engine)
