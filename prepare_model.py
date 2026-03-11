"""
Script to prepare model artifacts for production.
Re-fits the StandardScaler on training data and saves it.
Also copies the trained model to the models/ directory.
"""
import pandas as pd
import joblib
import os
import shutil
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_PATH = os.path.join(PROJECT_ROOT, "cardio_cleaned_week2.csv")
MODEL_SRC = os.path.join(PROJECT_ROOT, "model_fixed.pkl")
MODEL_DST = os.path.join(BASE_DIR, "models", "model.pkl")
SCALER_DST = os.path.join(BASE_DIR, "models", "scaler.pkl")

# Feature columns (same as training notebook - drops cardio, age, bmi_cat, id)
FEATURE_COLS = [
    "gender", "height", "weight", "ap_hi", "ap_lo",
    "cholesterol", "gluc", "smoke", "alco", "active",
    "age_years", "bmi", "MAP"
]

def main():
    print("Loading dataset...")
    df = pd.read_csv(DATA_PATH)
    
    X = df[FEATURE_COLS]
    y = df["cardio"]
    
    # Same split as notebook
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    print("Fitting StandardScaler on training data...")
    scaler = StandardScaler()
    scaler.fit(X_train)
    
    # Save scaler
    print(f"Saving scaler to {SCALER_DST}...")
    joblib.dump(scaler, SCALER_DST)
    
    # Copy model
    print(f"Copying model to {MODEL_DST}...")
    shutil.copy2(MODEL_SRC, MODEL_DST)
    
    # Verify
    print("\nVerifying artifacts...")
    loaded_model = joblib.load(MODEL_DST)
    loaded_scaler = joblib.load(SCALER_DST)
    
    X_test_scaled = loaded_scaler.transform(X_test)
    accuracy = loaded_model.score(X_test_scaled, y_test)
    print(f"Model accuracy on test set: {accuracy * 100:.2f}%")
    print("\nDone! Model artifacts are ready.")

if __name__ == "__main__":
    main()
