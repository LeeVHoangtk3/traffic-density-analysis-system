import { useEffect, useRef, useState } from "react";

const API = "http://127.0.0.1:8000";

function LightBulb({ color, active, hexColor, size = 40 }) {
  return (
    <div style={{
      width:        size,
      height:       size,
      borderRadius: "50%",
      background:   active ? hexColor : `${hexColor}22`,
      boxShadow:    active ? `0 0 16px 4px ${hexColor}88, 0 0 4px ${hexColor}` : "none",
      transition:   "all 0.4s ease",
      border:       `1px solid ${hexColor}44`,
    }} />
  );
}

function PhaseCard({ label, direction, isGreen, countdown, mode, extra }) {
  return (
    <div style={{
      flex:           1,
      padding:        "24px",
      background:     "rgba(255,255,255,0.04)",
      border:         `1px solid ${isGreen ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.2)"}`,
      borderRadius:   "14px",
      display:        "flex",
      flexDirection:  "column",
      alignItems:     "center",
      gap:            "16px",
      transition:     "border-color 0.4s",
    }}>
      <div style={{ fontSize: "12px", fontWeight: "600", color: "#64748b", letterSpacing: "0.08em", textAlign: "center" }}>
        {label}
      </div>

      {/* Traffic light housing */}
      <div style={{
        width:          "64px",
        background:     "#0d1117",
        border:         "2px solid rgba(255,255,255,0.1)",
        borderRadius:   "12px",
        padding:        "10px 12px",
        display:        "flex",
        flexDirection:  "column",
        gap:            "8px",
        alignItems:     "center",
      }}>
        <LightBulb hexColor="#ef4444" active={!isGreen} />
        <LightBulb hexColor="#f59e0b" active={false} />
        <LightBulb hexColor="#10b981" active={isGreen} />
      </div>

      {/* Countdown */}
      <div style={{ textAlign: "center" }}>
        <div style={{
          fontSize:   "48px",
          fontWeight: "800",
          color:      isGreen ? "#10b981" : "#ef4444",
          lineHeight: 1,
          fontVariantNumeric: "tabular-nums",
          textShadow: isGreen ? "0 0 20px rgba(16,185,129,0.4)" : "0 0 20px rgba(239,68,68,0.3)",
          transition: "color 0.4s",
        }}>
          {isGreen ? countdown : "—"}
        </div>
        <div style={{ fontSize: "11px", color: "#475569", marginTop: "4px" }}>
          {isGreen ? "giây còn lại" : "đang chờ"}
        </div>
      </div>

      {/* Phase badge */}
      <div style={{
        padding:      "4px 12px",
        borderRadius: "20px",
        background:   isGreen ? "rgba(16,185,129,0.12)" : "rgba(239,68,68,0.08)",
        border:       `1px solid ${isGreen ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.2)"}`,
        fontSize:     "11px",
        fontWeight:   "600",
        color:        isGreen ? "#10b981" : "#ef4444",
      }}>
        {isGreen ? "🟢 XANH" : "🔴 ĐỎ"}
      </div>

      <div style={{ fontSize: "10px", color: "#334155" }}>
        {extra}
      </div>
    </div>
  );
}

export default function TrafficLightPanel() {
  const [lightState, setLightState] = useState(null);
  const [countdown,  setCountdown]  = useState(0);
  const countdownRef = useRef(0);

  useEffect(() => {
    async function fetchLight() {
      try {
        const res  = await fetch(`${API}/traffic-lights/status`);
        const data = await res.json();
        setLightState(data);
        const serverSecs = Math.round(data.green_time ?? 30);
        if (Math.abs(countdownRef.current - serverSecs) > 3) {
          countdownRef.current = serverSecs;
          setCountdown(serverSecs);
        }
      } catch (e) {
        console.warn("[TrafficLight] fetch error:", e.message);
      }
    }
    fetchLight();
    const id = setInterval(fetchLight, 2000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const id = setInterval(() => {
      setCountdown(prev => {
        const next = prev > 0 ? prev - 1 : 0;
        countdownRef.current = next;
        return next;
      });
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const isLeftGreen = lightState?.phase === "left_green";

  return (
    <div style={styles.wrapper}>
      <div style={styles.header}>
        <span style={styles.dot} />
        TRAFFIC SIGNAL STATUS
      </div>

      <div style={styles.phases}>
        <PhaseCard
          label="PHA 1 — THẲNG & PHẢI"
          isGreen={!isLeftGreen}
          countdown={countdown}
          extra={`Mode: ${lightState?.mode ?? "—"} | Δ ${lightState?.delta ?? 0}s`}
        />
        <PhaseCard
          label="PHA 2 — RẼ TRÁI"
          isGreen={isLeftGreen}
          countdown={countdown}
          extra={`Baseline: ${lightState?.baseline ?? 30}s`}
        />
      </div>
    </div>
  );
}

const styles = {
  wrapper: {
    background:     "rgba(255,255,255,0.03)",
    border:         "1px solid rgba(255,255,255,0.08)",
    borderRadius:   "16px",
    padding:        "20px",
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
  phases: {
    display: "flex",
    gap:     "14px",
  },
};