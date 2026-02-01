from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./shop.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    name = Column(String)
    category = Column(String) # верх / низ
    in_stock = Column(Boolean, default=True)
    # Данные с сайта (Парсинг)
    parsed_chest = Column(Float)
    parsed_waist = Column(Float)
    parsed_hips = Column(Float)
    elasticity = Column(Float)

class MeasurementTest(Base):
    __tablename__ = "measurement_tests"
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String)
    product_id = Column(Integer, ForeignKey("products.id"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Что было у пользователя в профиле
    user_chest = Column(Float)
    user_waist = Column(Float)
    
    # Что мы намерили рулеткой в магазине
    real_garment_chest = Column(Float)
    real_garment_waist = Column(Float)
    
    # Итог: подошло или нет (0 - нет, 1 - да)
    fit_chest = Column(Boolean)
    fit_waist = Column(Boolean)
    conclusion = Column(String) # Общий вывод

Base.metadata.create_all(bind=engine)