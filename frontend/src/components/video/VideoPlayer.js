const API = "http://127.0.0.1:8000";

export default function VideoPlayer() {
  return (
    <div style={styles.wrapper}>
      <div style={styles.header}>
        <span style={styles.dot} />
        LIVE TRAFFIC FEED — CAM_01
        <span style={styles.liveBadge}>● LIVE</span>
      </div>

      <div style={styles.videoWrap}>
        <video
          style={styles.video}
          src={`${API}/video`}
          autoPlay
          loop
          muted
          playsInline
          controls
        />
        <div style={styles.overlay}>
          <span style={styles.camLabel}>CAM_01</span>
        </div>
      </div>
    </div>
  );
}

const styles = {
  wrapper: {
    background:   "rgba(255,255,255,0.03)",
    border:       "1px solid rgba(255,255,255,0.08)",
    borderRadius: "16px",
    padding:      "20px",
    overflow:     "hidden",
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
  liveBadge: {
    marginLeft:   "auto",
    fontSize:     "10px",
    fontWeight:   "700",
    color:        "#ef4444",
    letterSpacing: "0.05em",
    animation:    "pulse-live 1.5s ease-in-out infinite",
  },
  videoWrap: {
    position:     "relative",
    borderRadius: "10px",
    overflow:     "hidden",
    background:   "#000",
  },
  video: {
    width:   "100%",
    display: "block",
    maxHeight: "480px",
    objectFit: "cover",
  },
  overlay: {
    position: "absolute",
    top:      "10px",
    left:     "10px",
    padding:  "4px 10px",
    background: "rgba(0,0,0,0.6)",
    borderRadius: "6px",
    backdropFilter: "blur(4px)",
  },
  camLabel: {
    fontSize:   "11px",
    fontWeight: "700",
    color:      "#f1f5f9",
    letterSpacing: "0.08em",
  },
};