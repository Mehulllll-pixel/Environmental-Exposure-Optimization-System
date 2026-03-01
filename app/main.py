from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine
from .models import Base
from .optimization_engine import optimize

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