# AI-Based Personalized Environmental Exposure Optimization System

 Overview
A full-stack AI system that optimizes personal outdoor exposure by balancing environmental pollution risk and travel distance using multi-objective optimization.

 Problem
Urban residents face varying pollution exposure depending on location, time, and personal vulnerability. Traditional air quality systems do not personalize risk.

 Solution
This system computes a **Personalized Environmental Vulnerability Index (PEVI)** using:
- PM2.5
- PM10
- NO₂
- O₃
- CO

It incorporates:
- Age-based vulnerability weighting
- Health condition adjustments
- Duration-based exposure amplification
- Multi-objective optimization (risk vs distance)
- Geospatial Haversine distance computation

Optimization Model

Final Score:

FinalScore = α × PEVI_norm + (1 − α) × Distance_norm

Where:
- α = User risk preference
- PEVI_norm = Normalized exposure score
- Distance_norm = Normalized travel distance

The system minimizes FinalScore.

 Machine Learning
- XGBoost regression model for PM2.5 forecasting
- Model evaluation metrics:
  - RMSE
  - MAE
  - R² Score
- Feature importance analysis supported

 Geospatial Logic
- Haversine distance calculation
- Real-time station optimization
- Route visualization via Leaflet

 Analytics
- Exposure logging in PostgreSQL
- Risk distribution visualization
- PEVI trend over time
- User exposure summary endpoint

 Tech Stack

Backend:
- FastAPI
- SQLAlchemy
- PostgreSQL
- XGBoost
- Render (Cloud Deployment)

Frontend:
- React
- Chart.js
- Leaflet

 Deployment
Backend deployed on Render Cloud.
 Future Improvements
- Real-time AQI API integration
- User authentication
- Model retraining pipeline
- Predictive time-series forecasting
