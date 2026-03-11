import joblib

# load old model
model = joblib.load("final_model.pkl")

# save again with compatible environment
joblib.dump(model, "model_fixed.pkl")

print("Model re-saved successfully")