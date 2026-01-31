from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./shop.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    name = Column(String)
    image_url = Column(String)
    category = Column(String)
    in_stock = Column(Boolean, default=True)
    garment_chest = Column(Float, nullable=True)
    garment_waist = Column(Float, nullable=True)
    garment_hips = Column(Float, nullable=True)
    elasticity_percent = Column(Float, default=0)

Base.metadata.create_all(bind=engine)
.