import numpy as np
import pandas as pd
import xgboost as xgb
import os
from .vulnerability_engine import get_weights
from .explanation_engine import generate_explanation
from .models import ExposureLog
from .database import SessionLocal


# ==============================
# 🔥 Load ML Model at Startup
# ==============================

MODEL_PATH = os.path.join(os.path.dirname(__file__), "xgboost_pm25_model.json")

if os.path.exists(MODEL_PATH):
    model = xgb.XGBRegressor()
    model.load_model(MODEL_PATH)
    print("✅ XGBoost model loaded successfully")

    # 🔥 Optional: Evaluate model if dataset exists
    try:
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        import numpy as np

        if os.path.exists(DATA_PATH):
            temp_df = pd.read_csv(DATA_PATH)
            feature_cols = ["pm10", "no2", "o3", "co", "temperature", "humidity"]
            target_col = "pm25"

            if all(col in temp_df.columns for col in feature_cols + [target_col]):
                X = temp_df[feature_cols]
                y = temp_df[target_col]
                preds = model.predict(X)

                rmse = np.sqrt(mean_squared_error(y, preds))
                mae = mean_absolute_error(y, preds)
                r2 = r2_score(y, preds)

                print(f"📊 Model RMSE: {rmse:.2f}")
                print(f"📊 Model MAE: {mae:.2f}")
                print(f"📊 Model R2: {r2:.2f}")

    except Exception as e:
        print("⚠️ Model evaluation skipped:", e)

else:
    model = None
    print("⚠️ XGBoost model not found — using raw PM2.5")


# ==============================
# 🔥 Load Dataset at Startup
# ==============================

DATA_PATH = os.path.join(os.path.dirname(__file__), "delhi_forecasting_dataset.csv")

if os.path.exists(DATA_PATH):
    df_global = pd.read_csv(DATA_PATH)
    print("✅ Dataset loaded successfully")
else:
    df_global = None
    print("❌ Dataset not found")


# ==============================
# Risk Categorization
# ==============================

def categorize_risk(score):
    if score < 0.30:
        return "Safe"
    elif score < 0.60:
        return "Moderate"
    else:
        return "Avoid"


# ==============================
# Save User Exposure Log
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
        return {"error": "Dataset not loaded on server"}

    # Convert input date string
    input_date = pd.to_datetime(date)

    year = input_date.year
    month = input_date.month
    day = input_date.day

    # Filter dataset
    day_df = df_global[
        (df_global["year"] == year) &
        (df_global["month"] == month) &
        (df_global["day"] == day)
    ].copy()

    if day_df.empty:
        return {"error": "No data found for selected date"}

    # ==============================
    # 🔥 ML Prediction Step
    # ==============================

    if model is not None:
        required_features = ["pm10", "no2", "o3", "co", "hour"]

        # Ensure all required features exist
        if all(col in day_df.columns for col in required_features):
            X_input = day_df[required_features]
            day_df["pm25_predicted"] = model.predict(X_input)
        else:
            day_df["pm25_predicted"] = day_df["pm25"]
    else:
        day_df["pm25_predicted"] = day_df["pm25"]

    # ==============================
    # Personalized Vulnerability Weights
    # ==============================

    weights = get_weights(age_group, health_condition)

    day_df["PEVI"] = (
        weights["pm25"] * day_df["pm25_predicted"] +
        weights["pm10"] * day_df["pm10"] +
        weights["no2"] * day_df["no2"] +
        weights["o3"] * day_df["o3"] +
        weights["co"] * day_df["co"]
    )

    # Adjust by exposure duration
    duration_factor = 1 + (0.15 * duration_hours)
    day_df["PEVI_adjusted"] = day_df["PEVI"] * duration_factor

    # ==============================
    # Distance Calculation (Haversine)
    # ==============================

    R = 6371

    lat1 = np.radians(user_lat)
    lon1 = np.radians(user_lon)

    lat2 = np.radians(day_df["latitude"])
    lon2 = np.radians(day_df["longitude"])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))

    day_df["distance_km"] = R * c

    # ==============================
    # Multi-objective Optimization
    # ==============================

    day_df["distance_norm"] = day_df["distance_km"] / day_df["distance_km"].max()
    day_df["pevi_norm"] = day_df["PEVI_adjusted"] / day_df["PEVI_adjusted"].max()

    day_df["final_score"] = (
        preference * day_df["pevi_norm"] +
        (1 - preference) * day_df["distance_norm"]
    )

    best = day_df.loc[day_df["final_score"].idxmin()]

    city_avg_pevi = day_df["PEVI_adjusted"].mean()

    risk_level = categorize_risk(best["pevi_norm"])

    explanation = generate_explanation(best, city_avg_pevi, best["distance_km"])

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

    # Save exposure log
    save_exposure("anonymous_user", result)

    return result