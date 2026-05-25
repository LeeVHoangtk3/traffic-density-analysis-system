// Header.js — bỏ đồng hồ thực, hiện trạng thái hệ thống + thời gian video

import { useEffect, useState } from 'react';

const API = 'http://localhost:8000';

// format mm:ss or hh:mm:ss
function fmtVideoTime(secs) {
  const s = Math.floor(secs || 0);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  if (h > 0) return `${h}:${String(m).padStart(2,'0')}:${String(r).padStart(2,'0')}`;
  return `${String(m).padStart(2,'0')}:${String(r).padStart(2,'0')}`;
}

// format timestamp to HH:MM:SS
function fmtTs(ms) {
  if (!ms) return '--:--:--';
  try {
    return new Date(ms).toLocaleTimeString('vi-VN', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  } catch { return '--'; }
}

export default function Header({ videoStartMs, videoTime }) {
  const [dbStatus,  setDbStatus]  = useState('checking');
  const [serverTime, setServerTime] = useState(null);

  // ── health check ────────────────────────────────────
  useEffect(() => {
    async function check() {
      try {
        const r = await fetch(`${API}/health`);
        const d = await r.json();
        setDbStatus(d?.status === 'ok' && d?.database === 'ok' ? 'online' : 'error');
        if (d?.timestamp) setServerTime(new Date(d.timestamp));
      } catch {
        setDbStatus('offline');
      }
    }
    check();
    const id = setInterval(check, 10000);
    return () => clearInterval(id);
  }, []);

  const statusMap = {
    online:   { color: '#10b981', label: 'SYSTEM ONLINE' },
    error:    { color: '#f59e0b', label: 'DB ERROR'      },
    offline:  { color: '#ef4444', label: 'OFFLINE'       },
    checking: { color: '#6366f1', label: 'CHECKING...'   },
  };
  const { color, label } = statusMap[dbStatus] || statusMap.checking;

  // Thời gian hiện tại trong video (videoStartMs + videoTime)
  const currentVideoMs = videoStartMs ? videoStartMs + videoTime * 1000 : null;

  return (
    <header className="header">
      {/* LEFT — logo */}
      <div className="header-logo">
        <div className="header-icon">🚦</div>
        <div>
          <div className="header-title">CITY TRAFFIC MONITOR</div>
          <div className="header-subtitle">
            Real-time Traffic Intelligence System · Ho Chi Minh City
          </div>
        </div>
      </div>

      {/* CENTER — video time reference */}
      {videoStartMs && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 16,
          padding: '8px 20px',
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid var(--border)',
          borderRadius: 14,
        }}>
          {/* Origin */}
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.1em', color: 'var(--text-4)', textTransform: 'uppercase', marginBottom: 3 }}>
              Bắt đầu ghi
            </div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 14, fontWeight: 600, color: 'var(--text-2)' }}>
              {fmtTs(videoStartMs)}
            </div>
          </div>

          <div style={{ color: 'var(--text-4)', fontSize: 18, fontWeight: 300 }}>→</div>

          {/* Current video timestamp */}
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.1em', color: 'var(--yellow)', textTransform: 'uppercase', marginBottom: 3 }}>
              ▶ Thời điểm hiện tại
            </div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 14, fontWeight: 600, color: 'var(--text-1)' }}>
              {fmtTs(currentVideoMs)}
            </div>
          </div>

          <div style={{
            width: 1, height: 28, background: 'var(--border)', margin: '0 4px',
          }} />

          {/* Video elapsed time */}
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.1em', color: 'var(--blue-light)', textTransform: 'uppercase', marginBottom: 3 }}>
              Thời gian video
            </div>
            <div style={{
              fontFamily: 'JetBrains Mono, monospace', fontSize: 16, fontWeight: 700,
              color: 'var(--blue-light)',
            }}>
              {fmtVideoTime(videoTime)}
            </div>
          </div>
        </div>
      )}

      {/* RIGHT — status */}
      <div className="header-right">
        <div className="status-badge">
          <span className="status-dot" style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
          <span className="status-text">{label}</span>
        </div>
        {serverTime && (
          <div style={{
            fontSize: 10, color: 'var(--text-4)',
            fontFamily: 'JetBrains Mono, monospace',
          }}>
            SRV {serverTime.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </div>
        )}
      </div>
    </header>
  );
}