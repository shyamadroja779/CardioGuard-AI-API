"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


class MedicalInputs(BaseModel):
    """Medical input features for the cardiovascular disease prediction model."""
    gender: int = Field(..., ge=1, le=2, description="Gender: 1=Female, 2=Male")
    height: float = Field(..., gt=100, lt=250, description="Height in cm")
    weight: float = Field(..., gt=30, lt=300, description="Weight in kg")
    ap_hi: int = Field(..., ge=60, le=250, description="Systolic blood pressure")
    ap_lo: int = Field(..., ge=30, le=200, description="Diastolic blood pressure")
    cholesterol: int = Field(..., ge=1, le=3, description="Cholesterol: 1=Normal, 2=Above Normal, 3=Well Above Normal")
    gluc: int = Field(..., ge=1, le=3, description="Glucose: 1=Normal, 2=Above Normal, 3=Well Above Normal")
    smoke: int = Field(..., ge=0, le=1, description="Smoking: 0=No, 1=Yes")
    alco: int = Field(..., ge=0, le=1, description="Alcohol intake: 0=No, 1=Yes")
    active: int = Field(..., ge=0, le=1, description="Physical activity: 0=No, 1=Yes")
    age_years: float = Field(..., gt=0, lt=120, description="Age in years")


class PatientInfo(BaseModel):
    """Patient personal information."""
    full_name: str = Field(..., min_length=2, max_length=200, description="Patient full name")
    age: int = Field(..., gt=0, lt=120, description="Patient age")
    gender: str = Field(..., description="Patient gender display value")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    email: Optional[str] = Field(None, max_length=200, description="Email address")
    address: Optional[str] = Field(None, max_length=500, description="Address")


class DoctorInfo(BaseModel):
    """Doctor/Hospital information."""
    doctor_name: Optional[str] = Field(None, max_length=200, description="Doctor name")
    hospital_name: Optional[str] = Field(None, max_length=300, description="Hospital/Clinic name")


class PredictionRequest(BaseModel):
    """Full prediction request combining patient info, doctor info, and medical inputs."""
    patient: PatientInfo
    doctor: DoctorInfo
    medical: MedicalInputs


class PredictionResponse(BaseModel):
    """Prediction result response."""
    id: str
    prediction: int
    prediction_label: str
    probability: float
    risk_level: str
    recommendations: List[str]
    created_at: str


class ReportRequest(BaseModel):
    """Request to generate a PDF report."""
    prediction_id: str


class ReportResponse(BaseModel):
    """Report data response."""
    id: str
    patient_name: str
    patient_age: int
    patient_gender: str
    patient_phone: Optional[str]
    patient_email: Optional[str]
    patient_address: Optional[str]
    doctor_name: Optional[str]
    hospital_name: Optional[str]
    medical_inputs: Dict[str, Any]
    prediction: int
    prediction_label: str
    probability: float
    risk_level: str
    recommendations: List[str]
    created_at: str


class DashboardStats(BaseModel):
    """Public dashboard statistics."""
    total_predictions: int
    risk_distribution: Dict[str, int]
    model_accuracy: float
    recent_predictions: int
