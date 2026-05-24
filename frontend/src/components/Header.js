import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

export default function Header() {
  const [time,      setTime]      = useState(new Date());
  const [dbStatus,  setDbStatus]  = useState("checking");

  // Live clock
  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  // Health check moi 10 giay
  useEffect(() => {
    async function check() {
      try {
        const res  = await fetch(`${API}/health`);
        const data = await res.json();
        setDbStatus(data.database === "ok" ? "online" : "error");
      } catch {
        setDbStatus("offline");
      }
    }
    check();
    const id = setInterval(check, 10000);
    return () => clearInterval(id);
  }, []);

  const statusColor = {
    online:   "#10b981",
    error:    "#f97316",
    offline:  "#ef4444",
    checking: "#6366f1",
  }[dbStatus];

  return (
    <header style={styles.header}>

      <div style={styles.left}>
        <div style={styles.logo}>
          <span style={styles.logoIcon}>🚦</span>
          <div>
            <div style={styles.title}>CITY TRAFFIC MONITOR</div>
            <div style={styles.subtitle}>Real-time Traffic Intelligence System — CAM_01</div>
          </div>
        </div>
      </div>

      <div style={styles.right}>
        <div style={styles.statusBadge}>
          <span style={{ ...styles.statusDot, background: statusColor, boxShadow: `0 0 8px ${statusColor}` }} />
          <span style={styles.statusText}>
            {dbStatus === "online" ? "SYSTEM ONLINE" : dbStatus.toUpperCase()}
          </span>
        </div>

        <div style={styles.clock}>
          <div style={styles.clockTime}>
            {time.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
          </div>
          <div style={styles.clockDate}>
            {time.toLocaleDateString("vi-VN", { weekday: "short", day: "2-digit", month: "2-digit", year: "numeric" })}
          </div>
        </div>
      </div>

    </header>
  );
}

const styles = {
  header: {
    display:        "flex",
    alignItems:     "center",
    justifyContent: "space-between",
    padding:        "20px 28px",
    background:     "rgba(255,255,255,0.04)",
    border:         "1px solid rgba(255,255,255,0.08)",
    borderRadius:   "16px",
    backdropFilter: "blur(12px)",
  },
  left:   { display: "flex", alignItems: "center" },
  logo:   { display: "flex", alignItems: "center", gap: "14px" },
  logoIcon: { fontSize: "36px" },
  title: {
    fontSize:   "20px",
    fontWeight: "800",
    color:      "#f1f5f9",
    letterSpacing: "0.05em",
  },
  subtitle: {
    fontSize: "12px",
    color:    "#64748b",
    marginTop: "2px",
  },
  right: { display: "flex", alignItems: "center", gap: "24px" },
  statusBadge: {
    display:      "flex",
    alignItems:   "center",
    gap:          "8px",
    padding:      "6px 14px",
    background:   "rgba(255,255,255,0.05)",
    borderRadius: "20px",
    border:       "1px solid rgba(255,255,255,0.1)",
  },
  statusDot: {
    width:        "8px",
    height:       "8px",
    borderRadius: "50%",
  },
  statusText: {
    fontSize:   "11px",
    fontWeight: "600",
    color:      "#94a3b8",
    letterSpacing: "0.08em",
  },
  clock: { textAlign: "right" },
  clockTime: {
    fontSize:   "22px",
    fontWeight: "700",
    color:      "#f1f5f9",
    fontVariantNumeric: "tabular-nums",
  },
  clockDate: {
    fontSize: "11px",
    color:    "#64748b",
    marginTop: "2px",
  },
};