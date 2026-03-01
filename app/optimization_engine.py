import numpy as np
import pandas as pd
import os
from .vulnerability_engine import get_weights
from .explanation_engine import generate_explanation
from .models import ExposureLog
from .database import SessionLocal

# 🔥 Load dataset at startup
DATA_PATH = os.path.join(os.path.dirname(__file__), "delhi_forecasting_dataset.csv")

if os.path.exists(DATA_PATH):
    df_global = pd.read_csv(DATA_PATH)
else:
    df_global = None


def categorize_risk(score):
    if score < 0.30:
        return "Safe"
    elif score < 0.60:
        return "Moderate"
    else:
        return "Avoid"


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


def optimize(date, user_lat, user_lon,
             preference=0.7,
             age_group="adult",
             health_condition="none",
             duration_hours=1):

    if df_global is None:
        return {"error": "Dataset not loaded on server"}

    # Convert input date string into components
    input_date = pd.to_datetime(date)

    year = input_date.year
    month = input_date.month
    day = input_date.day

    day_df = df_global[
        (df_global["year"] == year) &
        (df_global["month"] == month) &
        (df_global["day"] == day)
        ].copy()

    if day_df.empty:
        return {"error": "No data found for selected date"}

    weights = get_weights(age_group, health_condition)

    day_df["PEVI"] = (
        weights["pm25"] * day_df["pm25"] +
        weights["pm10"] * day_df["pm10"] +
        weights["no2"] * day_df["no2"] +
        weights["o3"] * day_df["o3"] +
        weights["co"] * day_df["co"]
    )

    duration_factor = 1 + (0.15 * duration_hours)
    day_df["PEVI_adjusted"] = day_df["PEVI"] * duration_factor

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

    user_id = "anonymous_user"
    save_exposure(user_id, result)

    return result
