import React, { useState, useEffect } from "react";
import "./App.css";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler
);

const API = "http://localhost:8000";

export default function App() {
  const [stats, setStats] = useState({
    total: 0,
    car: 0,
    motorcycle: 0,
    truck: 0,
    bus: 0,
  });

  const [chart, setChart] = useState({
    labels: [],
    historicalData: [],
    predictedData: [],
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${API}/raw-data`);

        const result = await res.json();

        const data = result.items || [];
        let counts = {
          car: 0,
          motorcycle: 0,
          truck: 0,
          bus: 0,
        };

        data.forEach((e) => {
          const t = e.vehicle_type.toLowerCase();
          if (counts[t] !== undefined) counts[t]++;
        });

        setStats({
          total: data.length,
          ...counts,
        });

        const time = {};

        data.forEach((e) => {
          const d = new Date(e.timestamp);

          const key =
            d.getHours().toString().padStart(2, "0") +
            ":" +
            d.getMinutes().toString().padStart(2, "0");

          time[key] = (time[key] || 0) + 1;
        });

        const labels = Object.keys(time).sort().slice(-20);

        setChart({
          labels,
          historicalData: labels.map((k) => time[k]),
        });
      } catch (err) {
        console.log(err);
      }
    };

    fetchData();

    const i = setInterval(fetchData, 3000);

    return () => clearInterval(i);
  }, []);

  return (
    <div className="app">
      <div className="dashboard">

        <h1 className="title">CITY TRAFFIC MONITOR</h1>

        <div className="subtitle">
          REALTIME TRAFFIC STATISTICS
        </div>

        <div className="stats-grid">

          <div className="stat-card">
            <div className="stat-icon">🚘</div>
            <div>
              <div className="stat-label">Total Vehicles:</div>
              <div className="stat-value">{stats.total}</div>
            </div>
          </div>

          <div className="stat-card">
            <div className="yellow-dot"></div>
            <div>
              <div className="stat-label">Congestion Level:</div>
              <div className="stat-value">Medium</div>
            </div>
          </div>

          <div className="stat-card">
            <div>
              <div className="stat-label">
                Vehicle Classification
              </div>

              <div className="vehicle-row">
                <span>🚗 {stats.car}</span>
                <span>🏍️ {stats.motorcycle}</span>
                <span>🚚 {stats.truck + stats.bus}</span>
              </div>
            </div>
          </div>

          <div className="stat-card">
            <div className="chart-icon">📈</div>
            <div>
              <div className="stat-label">
                Traffic Prediction:
              </div>
              <div className="stat-value">
                Increasing 📈
              </div>
            </div>
          </div>

        </div>

        <div className="section-title">
          LIVE TRAFFIC FEED
        </div>

        <div className="video-wrapper">
          <video
            src="/traffictrim.mp4"
            autoPlay
            muted
            loop
            controls
          />
        </div>

        <div className="section-title chart-title">
          TRAFFIC VOLUME TREND (24H)
        </div>

        <div className="chart-container">
          <Line
            data={{
              labels: chart.labels,
              datasets: [
                {
                  label: "Traffic",
                  data: chart.historicalData,
                  borderColor: "#60a5fa",
                  backgroundColor: "rgba(96,165,250,0.15)",
                  fill: true,
                  tension: 0.4,
                  pointRadius: 0,
                },
              ],
            }}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  display: false,
                },
              },
              scales: {
                x: {
                  grid: {
                    display: false,
                  },
                },
                y: {
                  beginAtZero: true,
                  grid: {
                    color: "#eee",
                  },
                },
              },
            }}
          />
        </div>
      </div>
    </div>
  );
}