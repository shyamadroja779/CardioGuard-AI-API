"""
ML Model service - loads model and scaler, performs predictions.
"""
import os
import numpy as np
import joblib
from dotenv import load_dotenv

load_dotenv()

MODEL_PATH = os.getenv("MODEL_PATH", "models/model.pkl")
SCALER_PATH = os.getenv("SCALER_PATH", "models/scaler.pkl")

# Feature order must match training
FEATURE_ORDER = [
    "gender", "height", "weight", "ap_hi", "ap_lo",
    "cholesterol", "gluc", "smoke", "alco", "active",
    "age_years", "bmi", "MAP"
]

# Load model and scaler at module level
_model = None
_scaler = None


def _load_artifacts():
    global _model, _scaler
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, MODEL_PATH)
    scaler_path = os.path.join(base_dir, SCALER_PATH)
    
    _model = joblib.load(model_path)
    _scaler = joblib.load(scaler_path)
    print(f"Model loaded: {type(_model).__name__}")
    print(f"Scaler loaded: {type(_scaler).__name__}")


def get_model():
    if _model is None:
        _load_artifacts()
    return _model


def get_scaler():
    if _scaler is None:
        _load_artifacts()
    return _scaler


def compute_derived_features(medical_inputs: dict) -> dict:
    """
    Compute derived features (BMI and MAP) from raw inputs.
    These were engineered during data preprocessing.
    """
    height_m = medical_inputs["height"] / 100.0
    weight = medical_inputs["weight"]
    bmi = round(weight / (height_m ** 2), 2)
    
    ap_hi = medical_inputs["ap_hi"]
    ap_lo = medical_inputs["ap_lo"]
    map_val = round((ap_hi + 2 * ap_lo) / 3, 6)
    
    return {
        "bmi": bmi,
        "MAP": map_val
    }


def predict(medical_inputs: dict) -> dict:
    """
    Run prediction on medical inputs.
    Returns prediction (0/1), probability, and risk level.
    """
    model = get_model()
    scaler = get_scaler()
    
    # Compute derived features
    derived = compute_derived_features(medical_inputs)
    
    # Build feature vector in the correct order
    features = {}
    features.update(medical_inputs)
    features.update(derived)
    
    feature_vector = np.array([[features[f] for f in FEATURE_ORDER]])
    
    # Scale features
    feature_vector_scaled = scaler.transform(feature_vector)
    
    # Predict
    prediction = int(model.predict(feature_vector_scaled)[0])
    probabilities = model.predict_proba(feature_vector_scaled)[0]
    
    # Probability of positive class (cardiovascular disease)
    prob_positive = float(probabilities[1])
    
    # Determine risk level
    if prob_positive < 0.35:
        risk_level = "Low"
    elif prob_positive < 0.65:
        risk_level = "Medium"
    else:
        risk_level = "High"
    
    return {
        "prediction": prediction,
        "probability": round(prob_positive * 100, 2),
        "risk_level": risk_level,
        "derived_features": derived
    }


def get_recommendations(risk_level: str, medical_inputs: dict) -> list:
    """Generate health recommendations based on risk level and inputs."""
    recommendations = []
    
    # Universal recommendations
    recommendations.append("Schedule regular cardiovascular checkups with your healthcare provider.")
    
    if risk_level == "High":
        recommendations.append("⚠️ URGENT: Consult a cardiologist immediately for a comprehensive heart evaluation.")
        recommendations.append("Consider immediate lifestyle modifications under medical supervision.")
        recommendations.append("Monitor blood pressure daily and maintain a detailed health log.")
    elif risk_level == "Medium":
        recommendations.append("Schedule an appointment with your doctor to discuss preventive measures.")
        recommendations.append("Consider additional cardiac screening tests (ECG, stress test).")
    
    # Blood pressure specific
    if medical_inputs.get("ap_hi", 0) >= 140 or medical_inputs.get("ap_lo", 0) >= 90:
        recommendations.append("Your blood pressure readings are elevated. Reduce sodium intake and monitor BP regularly.")
    
    # Cholesterol specific
    if medical_inputs.get("cholesterol", 1) >= 2:
        recommendations.append("Elevated cholesterol detected. Adopt a heart-healthy diet low in saturated fats.")
    
    # Glucose specific
    if medical_inputs.get("gluc", 1) >= 2:
        recommendations.append("Elevated glucose levels detected. Monitor blood sugar and reduce refined carbohydrate intake.")
    
    # Smoking
    if medical_inputs.get("smoke", 0) == 1:
        recommendations.append("Smoking significantly increases cardiovascular risk. Consider a smoking cessation program.")
    
    # Alcohol
    if medical_inputs.get("alco", 0) == 1:
        recommendations.append("Limit alcohol consumption to reduce cardiovascular risk.")
    
    # Physical activity
    if medical_inputs.get("active", 0) == 0:
        recommendations.append("Incorporate at least 150 minutes of moderate aerobic exercise per week.")
    
    # BMI based
    height_m = medical_inputs.get("height", 170) / 100.0
    weight = medical_inputs.get("weight", 70)
    bmi = weight / (height_m ** 2)
    if bmi >= 30:
        recommendations.append("Your BMI indicates obesity. Work with a nutritionist to develop a healthy weight management plan.")
    elif bmi >= 25:
        recommendations.append("Your BMI indicates overweight. Maintain a balanced diet and increase physical activity.")
    
    recommendations.append("Maintain adequate hydration — drink at least 8 glasses of water daily.")
    recommendations.append("Practice stress management techniques such as meditation, yoga, or deep breathing.")
    recommendations.append("⚕️ Disclaimer: This is an AI-assisted assessment and should NOT replace professional medical advice.")
    
    return recommendations
