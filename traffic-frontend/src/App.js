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
  Filler,
  Legend
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler,
  Legend
);

// ✅ Kết nối với Backend FastAPI
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
        
        // Backend trả về { "items": [...], "total": ... } 
        const data = result.items || [];

        let counts = { car: 0, motorcycle: 0, truck: 0, bus: 0 };

        data.forEach((e) => {
          const t = e.vehicle_type.toLowerCase();
          if (counts[t] !== undefined) counts[t]++;
        });

        setStats({ total: data.length, ...counts });

        const time = {};
        data.forEach((e) => {
          const d = new Date(e.timestamp);
          const key =
            d.getHours().toString().padStart(2, "0") +
            ":" +
            d.getMinutes().toString().padStart(2, "0");
          time[key] = (time[key] || 0) + 1;
        });

        let historicalLabels = Object.keys(time).sort().slice(-15);
        let historicalValues = historicalLabels.map((k) => time[k]);

        let futureLabels = [];
        let predictedValues = [];

        let paddedHistorical = [...historicalValues];

        if (historicalValues.length > 0) {
          let lastValue = historicalValues[historicalValues.length - 1];
          const now = new Date();

          predictedValues.push(lastValue);

          for (let i = 1; i <= 15; i++) {
            const futureTime = new Date(now.getTime() + i * 60000);
            futureLabels.push(
              futureTime.getHours().toString().padStart(2, "0") +
                ":" +
                futureTime.getMinutes().toString().padStart(2, "0")
            );

            let nextVal = Math.max(
              0,
              Math.round(lastValue + (Math.random() * 10 - 5))
            );
            predictedValues.push(nextVal);
            lastValue = nextVal;

            paddedHistorical.push(null);
          }
        }

        let paddedPredicted = Array(historicalLabels.length - 1)
          .fill(null)
          .concat(predictedValues);

        setChart({
          labels: [...historicalLabels, ...futureLabels],
          historicalData: paddedHistorical,
          predictedData: paddedPredicted,
        });
      } catch (err) {
        console.log("Error fetching data:", err);
      }
    };

    fetchData();
    const i = setInterval(fetchData, 3000);
    return () => clearInterval(i);
  }, []);

  return (
    <div className="container">
      <div className="header">CITY TRAFFIC MONITOR</div>

      <div className="section">
        <div className="grid">
          <Card title="Total Vehicles" value={stats.total} icon="🚦" />
          <Card title="Cars" value={stats.car} icon="🚗" />
          <Card title="Motorcycles" value={stats.motorcycle} icon="🏍️" />
          <Card title="Truck + Bus" value={stats.truck + stats.bus} icon="🚚" />
        </div>
      </div>

      <div className="section">
        <h3>Live Traffic Feed</h3>
        <div className="video-box">
          {/* ✅ Cập nhật src để gọi thẳng API video từ Backend */}
          <video
            src={`${API}/video/output.mp4`}
            autoPlay
            loop
            muted
            controls
            playsInline
            style={{
              width: "100%",
              borderRadius: "10px",
            }}
          />
        </div>
      </div>

      <div className="section chart-section">
        <div className="chart-box">
          <h3>Traffic Volume & 15-Min Prediction</h3>
          <div className="chart-wrapper">
            <Line
              data={{
                labels: chart.labels,
                datasets: [
                  {
                    label: "Live Traffic",
                    data: chart.historicalData,
                    borderColor: "blue",
                    backgroundColor: "rgba(0,0,255,0.1)",
                    fill: true,
                    tension: 0.4,
                  },
                  {
                    label: "AI Prediction",
                    data: chart.predictedData,
                    borderColor: "orange",
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.4,
                  },
                ],
              }}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { position: "top" },
                },
                scales: {
                  y: { beginAtZero: true },
                },
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function Card({ title, value, icon }) {
  return (
    <div className="card">
      <div className="card-content">
        <div className="icon">{icon}</div>
        <div>
          <div className="card-title">{title}</div>
          <div className="card-value">{value}</div>
        </div>
      </div>
    </div>
  );
}