import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

const CARDS = [
  {
    key:   "vehicle_count",
    label: "Vehicles Detected",
    icon:  "🚗",
    unit:  "xe",
    color: "#6366f1",
  },
  {
    key:   "congestion_level",
    label: "Congestion Level",
    icon:  "📊",
    unit:  "",
    color: "#f59e0b",
  },
  {
    key:   "predicted",
    label: "Next Prediction",
    icon:  "🔮",
    unit:  "",
    color: "#a855f7",
  },
];

const CONGESTION_COLOR = {
  low:    "#10b981",
  medium: "#f59e0b",
  high:   "#f97316",
  heavy:  "#ef4444",
};

export default function StatsBar() {
  const [agg,  setAgg]  = useState(null);
  const [pred,  setPred]  = useState(null);

  useEffect(() => {
    async function fetchAll() {
      try {
        const [a, p] = await Promise.all([
          fetch(`${API}/aggregation/history?limit=1`).then(r => r.json()),
          fetch(`${API}/predictions/history?limit=1`).then(r => r.json()),
        ]);
        setAgg(a.items?.[0]  ?? null);
        setPred(p.items?.[0] ?? null);
      } catch (e) {
        console.warn("[StatsBar] fetch error:", e.message);
      }
    }

    fetchAll();
    const id = setInterval(fetchAll, 5000);
    return () => clearInterval(id);
  }, []);

  const congLevel = agg?.congestion_level ?? "—";
  const congColor = CONGESTION_COLOR[(congLevel ?? "").toLowerCase()] ?? "#94a3b8";

  const values = {
    vehicle_count:    agg?.vehicle_count ?? "—",
    congestion_level: congLevel,
    predicted:        pred?.predicted_congestion_level ?? "—",
  };

  return (
    <div style={styles.grid}>
      {CARDS.map(card => (
        <div key={card.key} style={styles.card}>
          <div style={{ ...styles.iconWrap, background: `${card.color}18`, border: `1px solid ${card.color}30` }}>
            <span style={styles.icon}>{card.icon}</span>
          </div>
          <div style={styles.info}>
            <div style={styles.label}>{card.label}</div>
            <div style={{
              ...styles.value,
              color: card.key === "congestion_level" ? congColor : card.color,
            }}>
              {values[card.key]}
              {card.unit && values[card.key] !== "—" && (
                <span style={styles.unit}> {card.unit}</span>
              )}
            </div>
          </div>
          <div style={{ ...styles.glow, background: `${card.color}08` }} />
        </div>
      ))}
    </div>
  );
}

const styles = {
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: "16px",
  },
  card: {
    position:       "relative",
    display:        "flex",
    alignItems:     "center",
    gap:            "14px",
    padding:        "18px 20px",
    background:     "rgba(255,255,255,0.04)",
    border:         "1px solid rgba(255,255,255,0.08)",
    borderRadius:   "14px",
    backdropFilter: "blur(12px)",
    overflow:       "hidden",
    transition:     "border-color 0.3s",
  },
  iconWrap: {
    width:          "44px",
    height:         "44px",
    borderRadius:   "10px",
    display:        "flex",
    alignItems:     "center",
    justifyContent: "center",
    flexShrink:     0,
  },
  icon:  { fontSize: "20px" },
  info:  { flex: 1 },
  label: { fontSize: "11px", color: "#64748b", fontWeight: "500", letterSpacing: "0.05em", marginBottom: "4px" },
  value: { fontSize: "26px", fontWeight: "700", lineHeight: 1 },
  unit:  { fontSize: "13px", fontWeight: "400", opacity: 0.7 },
  glow: {
    position:     "absolute",
    right:        0,
    top:          0,
    width:        "60px",
    height:       "100%",
    pointerEvents: "none",
  },
};