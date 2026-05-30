// Header.js — logo + system status only

import { useEffect, useState } from 'react';

const API = 'http://127.0.0.1:8000';

export default function Header({
  activeCamera,
  onChangeCamera,
  activeVideo,
  onChangeVideo,
  outputVideos = []
}) {
  const [dbStatus, setDbStatus] = useState('checking');

  useEffect(() => {
    async function check() {
      try {
        const r = await fetch(`${API}/health`);
        const d = await r.json();
        setDbStatus(d?.status === 'ok' && d?.database === 'ok' ? 'online' : 'error');
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

  // Lọc danh sách video: chỉ hiện các video thuộc camera đang chọn
  const filteredVideos = outputVideos.filter(vid => 
    vid.toLowerCase().startsWith(activeCamera.toLowerCase())
  );

  return (
    <header className="header">
      <div className="header-logo">
        <div className="header-icon">🚦</div>
        <div>
          <div className="header-title">CITY TRAFFIC MONITOR</div>
          <div className="header-subtitle">
            Real-time Traffic Intelligence System · Ho Chi Minh City
          </div>
        </div>
      </div>

      <div className="header-right">
        {/* Controls Container */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {/* Selector 1: SEGMENT */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-3)', letterSpacing: '0.04em' }}>SEGMENT:</span>
            <select
              value={activeCamera}
              onChange={(e) => onChangeCamera?.(e.target.value)}
              className="glass-select-btn"
            >
              <option value="cam01">🛣️ SEGMENT 01</option>
              <option value="cam02">🛣️ SEGMENT 02</option>
              <option value="cam03">🛣️ SEGMENT 03</option>
            </select>
          </div>

          {/* Selector 2: VIDEO */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-3)', letterSpacing: '0.04em' }}>VIDEO:</span>
            <select
              value={activeVideo}
              onChange={(e) => onChangeVideo?.(e.target.value)}
              className="glass-select-btn"
              style={{ maxWidth: '240px' }}
            >
              {filteredVideos.map((vid) => (
                <option key={vid} value={vid}>
                  🎬 {vid.replace('_output.mp4', '')}
                </option>
              ))}
              {filteredVideos.length === 0 && (
                <option value={activeVideo}>🎬 {activeVideo}</option>
              )}
            </select>
          </div>
        </div>

        <div className="status-badge">
          <span className="status-dot" style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
          <span className="status-text">{label}</span>
        </div>
      </div>
    </header>
  );
}