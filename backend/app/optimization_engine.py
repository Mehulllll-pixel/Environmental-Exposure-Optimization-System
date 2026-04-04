import numpy as np
import pandas as pd
import xgboost as xgb
import os
from .vulnerability_engine import get_weights
from .explanation_engine import generate_explanation
from .models import ExposureLog
from .database import SessionLocal

# ==============================
# 🔥 Paths
# ==============================

BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "xgboost_pm25_model.json")
DATA_PATH = os.path.join(BASE_DIR, "delhi_forecasting_dataset.csv")

# ==============================
# 🔥 Load Dataset
# ==============================

if os.path.exists(DATA_PATH):
    df_global = pd.read_csv(DATA_PATH)
    print("✅ Dataset loaded successfully")
else:
    df_global = None
    print("❌ Dataset not found")

# ==============================
# 🔥 Load Model
# ==============================

if os.path.exists(MODEL_PATH):
    model = xgb.XGBRegressor()
    model.load_model(MODEL_PATH)
    print("✅ XGBoost model loaded")
else:
    model = None
    print("⚠️ Model not found, using raw PM2.5")

# ==============================
# 🔥 Risk Categorization (FIXED)
# ==============================

def categorize_risk(score):
    if score < 0.40:
        return "Safe"
    elif score < 0.75:
        return "Moderate"
    else:
        return "Avoid"

# ==============================
# Save Exposure
# ==============================

def save_exposure(user_id, result):
    db = SessionLocal()

    log = ExposureLog(
        user_id=user_id,
        date=result["date"],
        station=result["recommended_station"],
        duration=result["duration_hours"],
        pevi_score=result["PEVI_score"],
        risk_level=result["risk_level"]
    )

    db.add(log)
    db.commit()
    db.close()

# ==============================
# 🔥 Main Optimization Function
# ==============================

def optimize(date, user_lat, user_lon,
             preference=0.7,
             age_group="adult",
             health_condition="none",
             duration_hours=1):

    if df_global is None:
        return {"error": "Dataset not loaded"}

    # Convert date
    input_date = pd.to_datetime(date)

    # Filter dataset
    day_df = df_global[
        (df_global["year"] == input_date.year) &
        (df_global["month"] == input_date.month) &
        (df_global["day"] == input_date.day)
    ].copy()

    # ==============================
    # 🔥 FUTURE DATE FIX (IMPORTANT)
    # ==============================

    if day_df.empty:
        day_df = df_global.copy()

        # Simulate realistic variation
        day_df["pm25"] += np.random.uniform(-10, 10, size=len(day_df))
        day_df["pm10"] += np.random.uniform(-5, 5, size=len(day_df))
        day_df["no2"] += np.random.uniform(-3, 3, size=len(day_df))

    # ==============================
    # 🔥 ML Prediction
    # ==============================

    if model is not None:
        required = ["pm10", "no2", "o3", "co", "hour"]

        if all(col in day_df.columns for col in required):
            X = day_df[required]
            day_df["pm25_predicted"] = model.predict(X)
        else:
            day_df["pm25_predicted"] = day_df["pm25"]
    else:
        day_df["pm25_predicted"] = day_df["pm25"]

    # ==============================
    # 🔥 Vulnerability Weights
    # ==============================

    weights = get_weights(age_group, health_condition)

    day_df["PEVI"] = (
        weights["pm25"] * day_df["pm25_predicted"] +
        weights["pm10"] * day_df["pm10"] +
        weights["no2"] * day_df["no2"] +
        weights["o3"] * day_df["o3"] +
        weights["co"] * day_df["co"]
    )

    # Duration impact
    duration_factor = 1 + (0.15 * duration_hours)
    day_df["PEVI_adjusted"] = day_df["PEVI"] * duration_factor

    # ==============================
    # 🔥 Distance Calculation
    # ==============================

    R = 6371

    lat1 = np.radians(user_lat)
    lon1 = np.radians(user_lon)

    lat2 = np.radians(day_df["latitude"])
    lon2 = np.radians(day_df["longitude"])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arcsin(np.sqrt(a))

    day_df["distance_km"] = R * c

    # ==============================
    # 🔥 Normalization (SAFE)
    # ==============================

    day_df["distance_norm"] = day_df["distance_km"] / (day_df["distance_km"].max() + 1e-6)
    day_df["pevi_norm"] = day_df["PEVI_adjusted"] / (day_df["PEVI_adjusted"].max() + 1e-6)

    # ==============================
    # 🔥 Multi-objective Optimization
    # ==============================

    day_df["final_score"] = (
        preference * day_df["pevi_norm"] +
        (1 - preference) * day_df["distance_norm"]
    )

    best = day_df.loc[day_df["final_score"].idxmin()]

    city_avg = day_df["PEVI_adjusted"].mean()

    risk_level = categorize_risk(best["pevi_norm"])

    explanation = generate_explanation(best, city_avg, best["distance_km"])

    # ==============================
    # 🔥 Result
    # ==============================

    result = {
        "date": date,
        "recommended_station": best["station"],
        "recommended_hour": int(best["hour"]),
        "safe_window": f"{int(best['hour'])}:00 - {int(best['hour'])+2}:00",
        "duration_hours": duration_hours,
        "PEVI_score": round(float(best["PEVI_adjusted"]), 2),
        "distance_km": round(float(best["distance_km"]), 2),
        "risk_level": risk_level,
        "station_lat": float(best["latitude"]),
        "station_lon": float(best["longitude"]),
        "explanation": explanation
    }

    # Save log
    save_exposure("user", result)

    return result