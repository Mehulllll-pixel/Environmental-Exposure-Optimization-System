from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine
from .models import Base
from .optimization_engine import optimize

from sqlalchemy import func
from .models import ExposureLog
from .database import SessionLocal


@app.get("/user-exposure-summary")
def exposure_summary(user_id: str = "anonymous_user"):
    db = SessionLocal()

    total = db.query(ExposureLog).filter(
        ExposureLog.user_id == user_id
    ).count()

    avg_pevi = db.query(func.avg(ExposureLog.pevi_score)).filter(
        ExposureLog.user_id == user_id
    ).scalar()

    most_station = db.query(
        ExposureLog.station,
        func.count(ExposureLog.station).label("count")
    ).filter(
        ExposureLog.user_id == user_id
    ).group_by(
        ExposureLog.station
    ).order_by(
        func.count(ExposureLog.station).desc()
    ).first()

    risk_counts = db.query(
        ExposureLog.risk_level,
        func.count(ExposureLog.risk_level)
    ).filter(
        ExposureLog.user_id == user_id
    ).group_by(
        ExposureLog.risk_level
    ).all()

    db.close()

    return {
        "total_exposures": total,
        "average_pevi": round(avg_pevi, 2) if avg_pevi else 0,
        "most_visited_station": most_station[0] if most_station else None,
        "risk_distribution": dict(risk_counts)
    }

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "Backend Running"}

@app.get("/optimize")
def optimize_route(
    date: str,
    user_lat: float,
    user_lon: float,
    preference: float = 0.7,
    age_group: str = "adult",
    health_condition: str = "none",
    duration_hours: int = 1
):
    return optimize(
        date,
        user_lat,
        user_lon,
        preference,
        age_group,
        health_condition,
        duration_hours
    )