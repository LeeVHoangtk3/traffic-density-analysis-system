import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

const LANES = [
  { key: "left",     label: "Làn Trái",   icon: "↩️",  dir: "left" },
  { key: "straight", label: "Làn Thẳng",  icon: "⬆️",  dir: "straight" },
  { key: "right",    label: "Làn Phải",   icon: "↪️",  dir: "right" },
];

const LEVEL_STYLE = {
  low:    { bg: "rgba(16,185,129,0.08)",  border: "rgba(16,185,129,0.3)",  text: "#10b981", label: "THẤP" },
  medium: { bg: "rgba(245,158,11,0.08)",  border: "rgba(245,158,11,0.3)",  text: "#f59e0b", label: "TRUNG BÌNH" },
  high:   { bg: "rgba(249,115,22,0.08)",  border: "rgba(249,115,22,0.3)",  text: "#f97316", label: "CAO" },
  heavy:  { bg: "rgba(239,68,68,0.10)",   border: "rgba(239,68,68,0.4)",   text: "#ef4444", label: "KẸT XE" },
};

const DEFAULT_STYLE = { bg: "rgba(255,255,255,0.04)", border: "rgba(255,255,255,0.08)", text: "#475569", label: "—" };

export default function LaneStatusGrid() {
  const [aggregations, setAggregations] = useState([]);

  useEffect(() => {
    async function fetch_() {
      try {
        const res  = await fetch(`${API}/aggregation/history?limit=10`);
        const data = await res.json();
        setAggregations(data.items ?? []);
      } catch (e) {
        console.warn("[LaneStatusGrid]", e.message);
      }
    }
    fetch_();
    const id = setInterval(fetch_, 5000);
    return () => clearInterval(id);
  }, []);

  const latest    = aggregations[0] ?? null;
  const getRecord = (idx) => aggregations[idx] ?? latest;

  return (
    <div style={styles.wrapper}>
      <div style={styles.header}>
        <span style={styles.dot} />
        LANE CONGESTION STATUS
      </div>

      <div style={styles.grid}>
        {LANES.map((lane, idx) => {
          const rec   = getRecord(idx);
          const level = (rec?.congestion_level ?? "").toLowerCase();
          const st    = LEVEL_STYLE[level] ?? DEFAULT_STYLE;
          const count = rec?.vehicle_count ?? "—";

          return (
            <div key={lane.key} style={{
              ...styles.card,
              background: st.bg,
              border:     `1px solid ${st.border}`,
              ...(level === "heavy" ? { animation: "pulse 1.2s ease-in-out infinite" } : {}),
            }}>
              <div style={styles.laneTop}>
                <span style={styles.laneIcon}>{lane.icon}</span>
                <span style={styles.laneName}>{lane.label}</span>
              </div>

              <div style={{ ...styles.laneCount, color: st.text }}>
                {count}
                {count !== "—" && <span style={styles.laneUnit}> xe</span>}
              </div>

              <div style={{
                ...styles.laneBadge,
                background: `${st.text}18`,
                color:      st.text,
                border:     `1px solid ${st.text}30`,
              }}>
                {st.label}
              </div>
            </div>
          );
        })}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.7; }
        }
      `}</style>
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
    color:         "#475569",
    marginBottom:  "16px",
  },
  dot: {
    width:        "6px",
    height:       "6px",
    borderRadius: "50%",
    background:   "#6366f1",
    boxShadow:    "0 0 6px #6366f1",
  },
  grid: { display: "flex", flexDirection: "column", gap: "10px" },
  card: {
    borderRadius: "10px",
    padding:      "14px 16px",
    display:      "flex",
    alignItems:   "center",
    gap:          "12px",
    transition:   "border-color 0.4s, background 0.4s",
  },
  laneTop: { display: "flex", alignItems: "center", gap: "6px", width: "100px" },
  laneIcon: { fontSize: "16px" },
  laneName: { fontSize: "13px", fontWeight: "600", color: "#94a3b8" },
  laneCount: { fontSize: "28px", fontWeight: "700", flex: 1, lineHeight: 1 },
  laneUnit:  { fontSize: "12px", fontWeight: "400", opacity: 0.6 },
  laneBadge: {
    padding:      "3px 10px",
    borderRadius: "20px",
    fontSize:     "10px",
    fontWeight:   "700",
    letterSpacing: "0.08em",
  },
};