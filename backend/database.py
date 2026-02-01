from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
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
    category = Column(String)
    in_stock = Column(Boolean, default=True)
    # Замеры изделия (с сайта)
    garment_chest = Column(Float)
    garment_waist = Column(Float)
    garment_hips = Column(Float)
    garment_shoulders = Column(Float)
    garment_sleeve = Column(Float)
    elasticity_percent = Column(Float, default=0.0)

class MeasurementTest(Base):
    __tablename__ = "measurement_tests"
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String)
    product_id = Column(Integer, ForeignKey("products.id"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    # Что было у юзера
    u_chest = Column(Float)
    u_waist = Column(Float)
    u_hips = Column(Float)
    # Что намерили в реале
    real_chest = Column(Float)
    real_waist = Column(Float)
    fit_ok = Column(Boolean)
    conclusion = Column(String)

Base.metadata.create_all(bind=engine)