// Header.js — logo + system status only

import { useEffect, useState } from 'react';

const API = 'http://localhost:8000';

export default function Header() {
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
        <div className="status-badge">
          <span className="status-dot" style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
          <span className="status-text">{label}</span>
        </div>
      </div>
    </header>
  );
}