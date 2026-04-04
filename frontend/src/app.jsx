import { useState, useEffect } from "react";
import axios from "axios";
import "./App.css";

import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
} from "chart.js";

import { Pie, Line } from "react-chartjs-2";

ChartJS.register(
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement
);

import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// 🔥 Backend URL
const API_BASE = "https://environmental-exposure-optimization.onrender.com";

// 🔥 Fix leaflet icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png",
  iconUrl:
    "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png",
  shadowUrl:
    "https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png",
});

// 🔥 Predefined stations (USER FRIENDLY)
const stations = [
  { name: "Mandir Marg", lat: 28.6366, lon: 77.2011 },
  { name: "Anand Vihar", lat: 28.6469, lon: 77.3164 },
  { name: "Wazirpur", lat: 28.6999, lon: 77.1653 },
  { name: "Jahangirpuri", lat: 28.7299, lon: 77.1718 },
];

function App() {
  const [date, setDate] = useState("2020-01-01");
  const [selectedStation, setSelectedStation] = useState(stations[0]);
  const [preference, setPreference] = useState(0.7);

  const [ageGroup, setAgeGroup] = useState("adult");
  const [healthCondition, setHealthCondition] = useState("none");
  const [duration, setDuration] = useState(1);

  const [result, setResult] = useState(null);
  const [summary, setSummary] = useState(null);
  const [trend, setTrend] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // ================= OPTIMIZE =================
  const handleOptimize = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await axios.get(`${API_BASE}/optimize`, {
        params: {
          date,
          user_lat: selectedStation.lat,
          user_lon: selectedStation.lon,
          preference,
          age_group: ageGroup,
          health_condition: healthCondition,
          duration_hours: duration,
        },
      });

      if (response.data.error) {
        setError(response.data.error);
        return;
      }

      setResult(response.data);
      fetchSummary();
      fetchTrend();

    } catch (err) {
      console.error(err);
      setError("Backend not responding. Try again.");
    } finally {
      setLoading(false);
    }
  };

  // ================= SUMMARY =================
  const fetchSummary = async () => {
    try {
      const res = await axios.get(`${API_BASE}/user-exposure-summary`);
      setSummary(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  // ================= TREND =================
  const fetchTrend = async () => {
    try {
      const res = await axios.get(`${API_BASE}/pevi-trend`);
      setTrend(res.data.trend);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchSummary();
    fetchTrend();
  }, []);

  const riskColor =
    result?.risk_level === "Safe"
      ? "#2ecc71"
      : result?.risk_level === "Moderate"
      ? "#f1c40f"
      : "#e74c3c";

  // 🔥 FIX PIE DATA
  const riskData = {
    Safe: summary?.risk_distribution?.Safe || 0,
    Moderate: summary?.risk_distribution?.Moderate || 0,
    Avoid: summary?.risk_distribution?.Avoid || 0,
  };

  return (
    <div className="container">
      <h1>🌍 AI Environmental Exposure Optimizer</h1>

      {/* ================= FORM ================= */}
      <div className="form">

        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />

        {/* 🔥 USER FRIENDLY LOCATION */}
        <select
          onChange={(e) =>
            setSelectedStation(
              stations.find((s) => s.name === e.target.value)
            )
          }
        >
          {stations.map((s) => (
            <option key={s.name}>{s.name}</option>
          ))}
        </select>

        <select value={ageGroup} onChange={(e) => setAgeGroup(e.target.value)}>
          <option value="child">Child</option>
          <option value="adult">Adult</option>
          <option value="elderly">Elderly</option>
        </select>

        <select
          value={healthCondition}
          onChange={(e) => setHealthCondition(e.target.value)}
        >
          <option value="none">No Health Condition</option>
          <option value="asthma">Asthma</option>
          <option value="cardiac">Cardiac</option>
        </select>

        <input
          type="number"
          min="1"
          max="8"
          value={duration}
          onChange={(e) => setDuration(parseInt(e.target.value))}
        />

        <div className="slider-section">
          <label>Risk Preference: {preference.toFixed(2)}</label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={preference}
            onChange={(e) =>
              setPreference(parseFloat(e.target.value))
            }
          />
        </div>

        <button onClick={handleOptimize}>🚀 Optimize</button>
      </div>

      {loading && <p>🔄 Optimizing...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {/* ================= RESULT ================= */}
      {result && (
        <>
          <div className="result-card">
            <h2>📍 Recommended Plan</h2>
            <p><strong>Station:</strong> {result.recommended_station}</p>
            <p><strong>Best Hour:</strong> {result.recommended_hour}:00</p>
            <p><strong>Safe Window:</strong> {result.safe_window}</p>
            <p><strong>PEVI Score:</strong> {result.PEVI_score}</p>
            <p><strong>Distance:</strong> {result.distance_km} km</p>

            <p>
              <strong>Risk:</strong>{" "}
              <span style={{ color: riskColor }}>
                {result.risk_level}
              </span>
            </p>

            <p><strong>AI Insight:</strong> {result.explanation}</p>
          </div>

          <MapContainer
            center={[result.station_lat, result.station_lon]}
            zoom={11}
            style={{ height: "400px", width: "80%", margin: "20px auto" }}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            <Marker position={[selectedStation.lat, selectedStation.lon]}>
              <Popup>Your Location</Popup>
            </Marker>

            <Marker position={[result.station_lat, result.station_lon]}>
              <Popup>{result.recommended_station}</Popup>
            </Marker>

            <Polyline
              positions={[
                [selectedStation.lat, selectedStation.lon],
                [result.station_lat, result.station_lon],
              ]}
            />
          </MapContainer>
        </>
      )}

      {/* ================= ANALYTICS ================= */}
      {summary && (
        <div className="analytics-card">
          <h2>📊 Exposure Analytics</h2>

          <p>Total: {summary.total_exposures}</p>
          <p>Avg PEVI: {summary.average_pevi}</p>
          <p>Top Location: {summary.most_visited_station}</p>

          <div style={{ width: "350px", margin: "20px auto" }}>
            <Pie
              data={{
                labels: ["Safe", "Moderate", "Avoid"],
                datasets: [
                  {
                    data: Object.values(riskData),
                    backgroundColor: ["#2ecc71", "#f1c40f", "#e74c3c"],
                  },
                ],
              }}
            />
          </div>
        </div>
      )}

      {/* ================= TREND ================= */}
      {trend && (
        <div style={{ width: "600px", margin: "40px auto" }}>
          <h3>📈 Pollution Trend</h3>
          <Line
            data={{
              labels: trend.map((t) => t.date),
              datasets: [
                {
                  label: "PEVI",
                  data: trend.map((t) => t.avg_pevi),
                  borderColor: "#00f2ff",
                },
              ],
            }}
          />
        </div>
      )}
    </div>
  );
}

export default App;