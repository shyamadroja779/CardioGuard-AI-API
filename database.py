"""
Database configuration and models for CardioGuard AI.
"""
import os
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cardio_predictions.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class PredictionRecord(Base):
    __tablename__ = "prediction_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Patient info
    patient_name = Column(String(200), nullable=False)
    patient_age = Column(Integer, nullable=False)
    patient_gender = Column(String(10), nullable=False)
    patient_phone = Column(String(20), nullable=True)
    patient_email = Column(String(200), nullable=True)
    patient_address = Column(Text, nullable=True)
    
    # Doctor info
    doctor_name = Column(String(200), nullable=True)
    hospital_name = Column(String(300), nullable=True)
    
    # Medical inputs (all 13 features stored as JSON)
    medical_inputs = Column(JSON, nullable=False)
    
    # Prediction results
    prediction = Column(Integer, nullable=False)  # 0 or 1
    probability = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)  # Low, Medium, High
    
    # Recommendations
    recommendations = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    report_generated = Column(Integer, default=0)


# Create tables
Base.metadata.create_all(bind=engine)
