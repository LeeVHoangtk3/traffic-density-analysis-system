// VideoPanel.js
// Stream video từ BE, theo dõi currentTime và gọi onTimeUpdate mỗi frame

import { useRef, useState, useEffect } from 'react';

function fmtTime(secs) {
  const s = Math.floor(secs || 0);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  if (h > 0) return `${h}:${String(m).padStart(2,'0')}:${String(r).padStart(2,'0')}`;
  return `${String(m).padStart(2,'0')}:${String(r).padStart(2,'0')}`;
}

export default function VideoPanel({ onTimeUpdate }) {
  const videoRef   = useRef(null);
  const rafRef     = useRef(null);
  const [displayTime, setDisplayTime] = useState(0);

  // ── Dùng requestAnimationFrame để cập nhật display time mỗi frame,
  //    nhưng chỉ gọi onTimeUpdate (gây re-render cha) mỗi 1 giây ─────
  useEffect(() => {
    let lastReportedSec = -1;

    function tick() {
      const el = videoRef.current;
      if (el) {
        const t = el.currentTime;
        setDisplayTime(t); // cập nhật badge trong VideoPanel (nhẹ)

        // Chỉ notify cha mỗi khi qua 1 giây mới → tránh re-render liên tục
        const currentSec = Math.floor(t);
        if (currentSec !== lastReportedSec) {
          lastReportedSec = currentSec;
          onTimeUpdate?.(t);
        }
      }
      rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [onTimeUpdate]);

  return (
    <div className="glass-card video-wrapper">
      {/* Top bar */}
      <div style={{
        padding: '12px 18px 10px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div className="section-title" style={{ margin: 0 }}>
          📹 CAMERA FEED · CAM_01
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <span style={{
            padding: '3px 10px',
            background: 'var(--red-dim)',
            border: '1px solid rgba(239,68,68,0.3)',
            borderRadius: 20,
            fontSize: 10, fontWeight: 700,
            color: 'var(--red)',
            letterSpacing: '0.08em',
          }}>● LIVE</span>
          <span style={{
            padding: '3px 10px',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid var(--border)',
            borderRadius: 20,
            fontSize: 10, fontWeight: 600,
            color: 'var(--text-3)',
          }}>traffic1.mp4</span>
        </div>
      </div>

      {/* Video + overlay */}
      <div style={{ position: 'relative' }}>
        <video
          ref={videoRef}
          src="http://localhost:8000/video"
          autoPlay
          muted
          loop
          controls
          style={{
            width: '100%',
            display: 'block',
            borderRadius: '0 0 var(--r-lg) var(--r-lg)',
            background: '#000',
            maxHeight: 500,
            objectFit: 'contain',
          }}
        />

        {/* Time badge overlay (top-left) */}
        <div style={{
          position: 'absolute',
          top: 10, left: 12,
          display: 'flex', alignItems: 'center', gap: 6,
          background: 'rgba(0,0,0,0.70)',
          border: '1px solid rgba(255,255,255,0.14)',
          borderRadius: 8,
          padding: '5px 11px',
          backdropFilter: 'blur(8px)',
          pointerEvents: 'none',
          zIndex: 10,
        }}>
          <span style={{
            width: 7, height: 7,
            background: 'var(--red)',
            borderRadius: '50%',
            animation: 'pulse-dot 1.2s ease infinite',
            display: 'inline-block',
          }} />
          <span style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 14,
            color: '#fff',
            fontWeight: 600,
            letterSpacing: '0.04em',
          }}>
            {fmtTime(displayTime)}
          </span>
        </div>

        {/* Info badge (top-right) */}
        <div style={{
          position: 'absolute',
          top: 10, right: 12,
          background: 'rgba(0,0,0,0.65)',
          border: '1px solid rgba(255,255,255,0.12)',
          borderRadius: 8,
          padding: '4px 10px',
          backdropFilter: 'blur(8px)',
          pointerEvents: 'none',
          zIndex: 10,
          fontSize: 11,
          color: 'rgba(255,255,255,0.7)',
          fontFamily: 'JetBrains Mono, monospace',
        }}>
          ⏱ {fmtTime(displayTime)}
        </div>
      </div>
    </div>
  );
}
