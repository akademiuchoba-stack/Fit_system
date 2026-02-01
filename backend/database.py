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
    size = Column(String) # S, M, L, 32/34 и т.д.
    image_url = Column(String, nullable=True)
    category = Column(String) # верх / низ
    in_stock = Column(Boolean, default=True)
    # Замеры изделия с сайта
    garment_chest = Column(Float, nullable=True)
    garment_waist = Column(Float, nullable=True)
    garment_hips = Column(Float, nullable=True)
    garment_shoulders = Column(Float, nullable=True)
    garment_sleeve = Column(Float, nullable=True)
    garment_height = Column(Float, nullable=True)
    elasticity_percent = Column(Float, default=0.0)

class MeasurementTest(Base):
    __tablename__ = "measurement_tests"
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String)
    product_id = Column(Integer, ForeignKey("products.id"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    u_chest = Column(Float)
    u_waist = Column(Float)
    u_hips = Column(Float)
    real_chest = Column(Float, nullable=True)
    real_waist = Column(Float, nullable=True)
    real_hips = Column(Float, nullable=True)
    fit_ok = Column(Boolean)
    conclusion = Column(String)

Base.metadata.create_all(bind=engine)