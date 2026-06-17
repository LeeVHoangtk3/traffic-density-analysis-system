import { useEffect, useState } from "react";
import {
  Chart as ChartJS,
  CategoryScale, LinearScale,
  PointElement, LineElement,
  Title, Tooltip, Legend, Filler,
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(
  CategoryScale, LinearScale,
  PointElement, LineElement,
  Title, Tooltip, Legend, Filler
);

const API = "http://127.0.0.1:8000";
const LEVEL_MAP = { low: 1, medium: 2, high: 3, heavy: 4 };

function levelToNum(s)  { return LEVEL_MAP[(s ?? "").toLowerCase()] ?? 0; }
function shortTime(iso) {
  if (!iso) return "";
  try { return new Date(iso).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }); }
  catch { return iso; }
}

export default function ForecastChart() {
  const [predictions,  setPredictions]  = useState([]);
  const [aggregations, setAggregations] = useState([]);

  useEffect(() => {
    async function fetchP() {
      try {
        const res  = await fetch(`${API}/predictions/history?limit=10`);
        const data = await res.json();
        setPredictions(data.items ?? []);
      } catch (e) { console.warn("[ForecastChart]", e.message); }
    }
    fetchP();
    const id = setInterval(fetchP, 5000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    async function fetchA() {
      try {
        const res  = await fetch(`${API}/aggregation/history?limit=10`);
        const data = await res.json();
        setAggregations(data.items ?? []);
      } catch (e) { console.warn("[ForecastChart]", e.message); }
    }
    fetchA();
    const id = setInterval(fetchA, 5000);
    return () => clearInterval(id);
  }, []);

  const preds  = [...predictions].reverse().slice(0, 10);
  const aggs   = [...aggregations].reverse().slice(0, 10);
  const labels = (preds.length ? preds : aggs).map(i => shortTime(i.timestamp));

  const chartData = {
    labels,
    datasets: [
      {
        label:           "Dự báo (Predicted)",
        data:            preds.map(p => levelToNum(p.predicted_congestion_level)),
        borderColor:     "#6366f1",
        backgroundColor: "rgba(99,102,241,0.08)",
        borderWidth:     2,
        pointBackgroundColor: "#6366f1",
        pointRadius:     4,
        tension:         0.4,
        fill:            true,
      },
      {
        label:           "Thực tế (Actual)",
        data:            aggs.map(a => levelToNum(a.congestion_level)),
        borderColor:     "#10b981",
        backgroundColor: "rgba(16,185,129,0.08)",
        borderWidth:     2,
        pointBackgroundColor: "#10b981",
        pointRadius:     4,
        tension:         0.4,
        fill:            true,
      },
    ],
  };

  const options = {
    responsive:          true,
    maintainAspectRatio: false,
    interaction:         { mode: "index", intersect: false },
    plugins: {
      legend: {
        position: "top",
        labels:   { color: "#f1f5f9", font: { size: 12, family: "Inter" }, boxWidth: 12, padding: 20 },
      },
    },
    scales: {
      x: {
        ticks: { color: "#cbd5e1", font: { size: 11 } },
        grid:  { color: "rgba(255,255,255,0.04)" },
      },
      y: {
        min: 0, max: 5,
        ticks: {
          color:    "#cbd5e1",
          font:     { size: 11 },
          stepSize: 1,
          callback: v => ({ 1: "Low", 2: "Medium", 3: "High", 4: "Heavy" }[v] ?? ""),
        },
        grid: { color: "rgba(255,255,255,0.04)" },
      },
    },
  };

  return (
    <div style={styles.wrapper}>
      <div style={styles.header}>
        <span style={styles.dot} />
        FORECAST vs ACTUAL — CONGESTION LEVEL HISTORY
      </div>
      {(!preds.length && !aggs.length) ? (
        <div style={styles.empty}>Chưa có dữ liệu dự báo...</div>
      ) : (
        <div style={{ height: "260px" }}>
          <Line data={chartData} options={options} />
        </div>
      )}
    </div>
  );
}

const styles = {
  wrapper: {
    background:   "rgba(255,255,255,0.03)",
    border:       "1px solid rgba(255,255,255,0.08)",
    borderRadius: "16px",
    padding:      "20px",
  },
  header: {
    display:       "flex",
    alignItems:    "center",
    gap:           "8px",
    fontSize:      "11px",
    fontWeight:    "600",
    letterSpacing: "0.1em",
    color:         "#94a3b8",
    marginBottom:  "16px",
  },
  dot: {
    width:        "6px",
    height:       "6px",
    borderRadius: "50%",
    background:   "#6366f1",
    boxShadow:    "0 0 6px #6366f1",
  },
  empty: {
    height:         "260px",
    display:        "flex",
    alignItems:     "center",
    justifyContent: "center",
    color:          "#334155",
    fontSize:       "14px",
  },
};