"""
CardioGuard AI - FastAPI Backend
Cardiovascular Disease Prediction API with PDF Report Generation
"""
import os
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import io

from database import get_db, PredictionRecord, Base, engine
from schemas import (
    PredictionRequest, PredictionResponse,
    ReportRequest, ReportResponse, DashboardStats
)
from ml_service import predict, get_recommendations, compute_derived_features
from pdf_generator import generate_report_pdf

load_dotenv()

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="CardioGuard AI API",
    description="AI-Powered Cardiovascular Disease Prediction System",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure tables exist
Base.metadata.create_all(bind=engine)


@app.get("/")
async def root():
    return {
        "name": "CardioGuard AI API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "predict": "POST /predict",
            "generate_report": "POST /generate-report",
            "get_report": "GET /report/{id}",
            "dashboard": "GET /dashboard",
        }
    }


@app.post("/predict", response_model=PredictionResponse)
@limiter.limit("30/minute")
async def create_prediction(request: Request, data: PredictionRequest, db: Session = Depends(get_db)):
    """
    Run cardiovascular disease prediction.
    Accepts patient info, doctor info, and medical inputs.
    Returns prediction result with probability and risk level.
    """
    try:
        # Extract medical inputs as dict
        medical_dict = data.medical.model_dump()
        
        # Run prediction
        result = predict(medical_dict)
        
        # Get recommendations
        recommendations = get_recommendations(result["risk_level"], medical_dict)
        
        # Add derived features to medical inputs for storage
        derived = result.get("derived_features", {})
        stored_medical = {**medical_dict, **derived}
        
        # Create database record
        record = PredictionRecord(
            patient_name=data.patient.full_name,
            patient_age=data.patient.age,
            patient_gender=data.patient.gender,
            patient_phone=data.patient.phone,
            patient_email=data.patient.email,
            patient_address=data.patient.address,
            doctor_name=data.doctor.doctor_name,
            hospital_name=data.doctor.hospital_name,
            medical_inputs=stored_medical,
            prediction=result["prediction"],
            probability=result["probability"],
            risk_level=result["risk_level"],
            recommendations=recommendations,
        )
        
        db.add(record)
        db.commit()
        db.refresh(record)
        
        prediction_label = "Cardiovascular Disease Detected" if result["prediction"] == 1 else "No Cardiovascular Disease"
        
        return PredictionResponse(
            id=record.id,
            prediction=result["prediction"],
            prediction_label=prediction_label,
            probability=result["probability"],
            risk_level=result["risk_level"],
            recommendations=recommendations,
            created_at=record.created_at.isoformat() if record.created_at else datetime.now(timezone.utc).isoformat(),
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/generate-report")
@limiter.limit("10/minute")
async def generate_report(request: Request, data: ReportRequest, db: Session = Depends(get_db)):
    """
    Generate a PDF report for a given prediction ID.
    Returns the PDF file as a downloadable stream.
    """
    record = db.query(PredictionRecord).filter(
        PredictionRecord.id == data.prediction_id
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Prediction record not found")
    
    try:
        pdf_bytes = generate_report_pdf(record)
        
        # Update report generated flag
        record.report_generated = 1
        db.commit()
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="CardioGuard_Report_{record.id[:8].upper()}.pdf"',
                "Content-Length": str(len(pdf_bytes)),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@app.get("/report/{prediction_id}", response_model=ReportResponse)
async def get_report(prediction_id: str, db: Session = Depends(get_db)):
    """
    Fetch report data by prediction ID.
    """
    record = db.query(PredictionRecord).filter(
        PredictionRecord.id == prediction_id
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Report not found")
    
    prediction_label = "Cardiovascular Disease Detected" if record.prediction == 1 else "No Cardiovascular Disease"
    
    return ReportResponse(
        id=record.id,
        patient_name=record.patient_name,
        patient_age=record.patient_age,
        patient_gender=record.patient_gender,
        patient_phone=record.patient_phone,
        patient_email=record.patient_email,
        patient_address=record.patient_address,
        doctor_name=record.doctor_name,
        hospital_name=record.hospital_name,
        medical_inputs=record.medical_inputs or {},
        prediction=record.prediction,
        prediction_label=prediction_label,
        probability=record.probability,
        risk_level=record.risk_level,
        recommendations=record.recommendations or [],
        created_at=record.created_at.isoformat() if record.created_at else "",
    )


@app.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(db: Session = Depends(get_db)):
    """
    Get public dashboard statistics.
    """
    total = db.query(func.count(PredictionRecord.id)).scalar() or 0
    
    risk_low = db.query(func.count(PredictionRecord.id)).filter(
        PredictionRecord.risk_level == "Low"
    ).scalar() or 0
    
    risk_medium = db.query(func.count(PredictionRecord.id)).filter(
        PredictionRecord.risk_level == "Medium"
    ).scalar() or 0
    
    risk_high = db.query(func.count(PredictionRecord.id)).filter(
        PredictionRecord.risk_level == "High"
    ).scalar() or 0
    
    # Recent predictions (last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent = db.query(func.count(PredictionRecord.id)).filter(
        PredictionRecord.created_at >= week_ago
    ).scalar() or 0
    
    return DashboardStats(
        total_predictions=total,
        risk_distribution={
            "Low": risk_low,
            "Medium": risk_medium,
            "High": risk_high,
        },
        model_accuracy=73.22,
        recent_predictions=recent,
    )


@app.get("/report/{prediction_id}/pdf")
async def get_report_pdf(prediction_id: str, db: Session = Depends(get_db)):
    """
    Get the PDF report directly by prediction ID (for browser preview).
    """
    record = db.query(PredictionRecord).filter(
        PredictionRecord.id == prediction_id
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Report not found")
    
    try:
        pdf_bytes = generate_report_pdf(record)
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="CardioGuard_Report_{record.id[:8].upper()}.pdf"',
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
