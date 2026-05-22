import React, { useState, useEffect, useCallback } from "react";
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

const API_BASE = "http://localhost:8000";
const CAMERA_ID = "CAM_01";

export default function App() {
  const [isLive, setIsLive] = useState(true);
  const [isOnline, setIsOnline] = useState(false);
  const [metrics, setMetrics] = useState({
    totalToday: 0,
    congestion: "Low",
    forecast15m: 0,
    lastDelta: 0
  });
  const [chartData, setChartData] = useState({
    labels: [],
    actual: [],
    predicted: []
  });
  const [trafficLights, setTrafficLights] = useState([
    { id: "CAM_01", baseline: 30, delta: 0, green: 30, status: "Low" },
    { id: "CAM_02", baseline: 25, delta: 0, green: 25, status: "Low" },
    { id: "CAM_03", baseline: 35, delta: 0, green: 35, status: "Low" }
  ]);
  const [logs, setLogs] = useState([]);
  const [camStats, setCamStats] = useState({ count: 0, density: 0 });

  const fetchLiveData = useCallback(async () => {
    try {
      // 1. Check health
      const healthRes = await fetch(`${API_BASE}/health`).catch(() => null);
      setIsOnline(!!healthRes && healthRes.ok);

      if (!healthRes || !healthRes.ok) return;

      // 2. Fetch Aggregation
      const aggRes = await fetch(`${API_BASE}/aggregation?camera_id=${CAMERA_ID}`);
      const aggData = await aggRes.json();

      // 3. Fetch Raw Data for logs
      const rawRes = await fetch(`${API_BASE}/raw-data?limit=10`);
      const rawData = await rawRes.json();

      // Update Metrics & State
      setMetrics(prev => ({
        ...prev,
        totalToday: rawData.total || 0,
        congestion: aggData.congestion_level || "Low",
      }));

      setCamStats({
        count: aggData.vehicle_count || 0,
        density: (aggData.vehicle_count / 100).toFixed(2)
      });

      setLogs(rawData.items || []);

      // Mocking delta and forecast for now as API might not provide them yet
      setMetrics(prev => ({
        ...prev,
        lastDelta: (Math.random() * 20 - 5).toFixed(1),
        forecast15m: Math.round(aggData.vehicle_count * (1 + Math.random() * 0.2))
      }));

      // Update Light Table (mocking for others, actual for CAM_01)
      setTrafficLights(prev => prev.map(l => {
        if (l.id === CAMERA_ID) {
          const delta = (Math.random() * 15 - 5).toFixed(1);
          return { ...l, delta, green: (l.baseline + parseFloat(delta)).toFixed(1), status: aggData.congestion_level };
        }
        return l;
      }));

      // Update Chart
      const now = new Date();
      const timeLabel = now.getHours() + ":" + now.getMinutes().toString().padStart(2, "0");
      setChartData(prev => {
        const newLabels = [...prev.labels, timeLabel].slice(-15);
        const newActual = [...prev.actual, aggData.vehicle_count].slice(-15);
        const newPred = [...prev.predicted, Math.round(aggData.vehicle_count * (0.9 + Math.random() * 0.2))].slice(-15);
        return { labels: newLabels, actual: newActual, predicted: newPred };
      });

    } catch (err) {
      console.error("Fetch error:", err);
      setIsOnline(false);
    }
  }, []);

  const generateMockData = useCallback(() => {
    setIsOnline(true);
    const count = Math.floor(Math.random() * 60);
    const levels = ["Low", "Medium", "High", "Severe"];
    const level = count < 15 ? "Low" : count < 30 ? "Medium" : count < 50 ? "High" : "Severe";

    setMetrics({
      totalToday: 1240 + Math.floor(Math.random() * 100),
      congestion: level,
      forecast15m: Math.round(count * 1.2),
      lastDelta: (Math.random() * 30 - 10).toFixed(1)
    });

    setCamStats({ count, density: (count / 100).toFixed(2) });

    setTrafficLights(prev => prev.map(l => {
      const delta = (Math.random() * 20 - 5).toFixed(1);
      return { ...l, delta, green: (l.baseline + parseFloat(delta)).toFixed(1), status: level };
    }));

    const now = new Date();
    const timeLabel = now.getHours() + ":" + now.getMinutes().toString().padStart(2, "0");
    setChartData(prev => ({
      labels: [...prev.labels, timeLabel].slice(-15),
      actual: [...prev.actual, count].slice(-15),
      predicted: [...prev.predicted, Math.round(count * 1.1)].slice(-15)
    }));

    setLogs(prev => [
      { timestamp: new Date().toISOString(), camera_id: "CAM_01", vehicle_type: "Car", direction: "Inbound" },
      ...prev
    ].slice(0, 10));
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      if (isLive) fetchLiveData();
      else generateMockData();
    }, 5000);
    return () => clearInterval(timer);
  }, [isLive, fetchLiveData, generateMockData]);

  return (
    <div className="container">
      {/* Header */}
      <div className="header-area">
        <div className="logo-text">TRAFFIC AI PULSE</div>
        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
          <div className="mode-toggle" onClick={() => setIsLive(!isLive)}>
            <span style={{ fontSize: '12px' }}>{isLive ? 'LIVE MODE' : 'DEMO MODE'}</span>
            <div className={`switch ${isLive ? 'active' : ''}`}></div>
          </div>
          <div className="status-indicator">
            <div className={`dot ${isOnline ? 'pulse' : 'offline'}`}></div>
            <span>{isOnline ? 'SYSTEM ONLINE' : 'SYSTEM OFFLINE'}</span>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="dashboard-grid">
        <MetricCard label="Total Vehicles Today" value={metrics.totalToday} icon="🚗" />
        <MetricCard label="Current Congestion" value={metrics.congestion} color={metrics.congestion} />
        <MetricCard label="15-Min Forecast" value={metrics.forecast15m} unit="vehicles" />
        <MetricCard label="Last Light Delta" value={metrics.lastDelta} unit="sec" trend={metrics.lastDelta > 0 ? 'up' : 'down'} />
      </div>

      {/* Main Content */}
      <div className="main-layout">
        {/* Left: Camera & Lights */}
        <div style={{ display: 'flex', flex_direction: 'column', gap: '24px' }}>
          <div className="panel">
            <div className="panel-title">📹 Live Stream Simulation</div>
            <div className="camera-box">
              <div className="zone-overlay">
                <div className="zone-label">DETECTION ZONE A</div>
              </div>
              {[...Array(5)].map((_, i) => (
                <div key={i} className="car-sim" style={{ animationDelay: `${i * 0.8}s` }}></div>
              ))}
              <div className="camera-info">
                ID: {CAMERA_ID} | COUNT: {camStats.count} | DENSITY: {camStats.density}
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-title">🚥 Traffic Light Management</div>
            <table className="light-table">
              <thead>
                <tr>
                  <th>CAMERA</th>
                  <th>BASELINE</th>
                  <th>DELTA</th>
                  <th>GREEN TIME</th>
                  <th>STATUS</th>
                  <th>INDICATOR</th>
                </tr>
              </thead>
              <tbody>
                {trafficLights.map(light => (
                  <tr key={light.id}>
                    <td style={{ fontWeight: 600 }}>{light.id}</td>
                    <td>{light.baseline}s</td>
                    <td style={{ color: light.delta >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                      {light.delta >= 0 ? '+' : ''}{light.delta}s
                    </td>
                    <td style={{ fontSize: '16px', fontWeight: 700 }}>{light.green}s</td>
                    <td>
                      <span className={`status-badge status-${light.status.toLowerCase()}`}>
                        {light.status}
                      </span>
                    </td>
                    <td>
                      <TrafficLightSVG status={light.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Charts & Logs */}
        <div style={{ display: 'flex', flex_direction: 'column', gap: '24px' }}>
          <div className="panel" style={{ flex: 1 }}>
            <div className="panel-title">📊 Density Analysis</div>
            <div className="chart-container">
              <Line
                data={{
                  labels: chartData.labels,
                  datasets: [
                    {
                      label: "Actual Count",
                      data: chartData.actual,
                      borderColor: "#00f2fe",
                      backgroundColor: "rgba(0, 242, 254, 0.1)",
                      fill: true,
                      tension: 0.4
                    },
                    {
                      label: "AI Prediction",
                      data: chartData.predicted,
                      borderColor: "#f093fb",
                      borderDash: [5, 5],
                      fill: false,
                      tension: 0.4
                    }
                  ]
                }}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  scales: {
                    y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#888' } },
                    x: { grid: { display: false }, ticks: { color: '#888' } }
                  },
                  plugins: { legend: { labels: { color: '#eee' } } }
                }}
              />
            </div>
          </div>

          <div className="panel">
            <div className="panel-title">📜 Real-time Event Log</div>
            <div className="event-log">
              {logs.map((log, i) => (
                <div key={i} className="log-item">
                  <span className="log-ts">{new Date(log.timestamp).toLocaleTimeString()}</span>
                  <span className="log-cam">{log.camera_id}</span>
                  <span className="log-msg">Detected {log.vehicle_type} going {log.direction}</span>
                </div>
              ))}
              {logs.length === 0 && <div style={{ color: '#555', textAlign: 'center', padding: '20px' }}>No events detected</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, icon, unit, color, trend }) {
  const colorClass = color ? `status-${color.toLowerCase()}` : '';
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${colorClass}`}>
        {icon && <span style={{ marginRight: '10px' }}>{icon}</span>}
        {value}
        {unit && <span className="metric-unit">{unit}</span>}
        {trend && <span style={{ fontSize: '12px', marginLeft: '5px' }}>{trend === 'up' ? '▲' : '▼'}</span>}
      </div>
    </div>
  );
}

function TrafficLightSVG({ status }) {
  const s = status.toLowerCase();
  const red = (s === 'high' || s === 'severe') ? 'var(--danger)' : '#222';
  const yellow = (s === 'medium') ? 'var(--warning)' : '#222';
  const green = (s === 'low') ? 'var(--success)' : '#222';

  return (
    <svg className="light-svg" viewBox="0 0 40 100">
      <rect x="5" y="0" width="30" height="90" rx="15" fill="#111" stroke="rgba(255,255,255,0.1)" />
      <circle cx="20" cy="20" r="10" fill={red} />
      <circle cx="20" cy="45" r="10" fill={yellow} />
      <circle cx="20" cy="70" r="10" fill={green} />
    </svg>
  );
}