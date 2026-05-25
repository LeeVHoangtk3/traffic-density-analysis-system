// VehicleTypes.js
// Phân loại xe từ rawData (filteredRaw) → tăng dần theo video

const VEHICLE_DEFS = [
  { type: 'car',        icon: '🚗', label: 'Ô tô',    color: '#3b82f6' },
  { type: 'motorcycle', icon: '🏍️', label: 'Xe máy',  color: '#10b981' },
  { type: 'truck',      icon: '🚛', label: 'Xe tải',  color: '#f59e0b' },
  { type: 'bus',        icon: '🚌', label: 'Xe buýt', color: '#a855f7' },
];

const LANE_DEFS = [
  { dir: 'left',     symbol: '←', color: '#10b981' },
  { dir: 'straight', symbol: '↑', color: '#f59e0b' },
  { dir: 'right',    symbol: '→', color: '#ef4444' },
];

function groupByType(data) {
  const counts = { car: 0, motorcycle: 0, truck: 0, bus: 0 };
  data.forEach(item => {
    const t = (item.vehicle_type || '').toLowerCase();
    if (t in counts) counts[t]++;
  });
  return counts;
}

export default function VehicleTypes({ rawData = [] }) {
  const counts = groupByType(rawData);
  const total  = rawData.length || 1; // tổng từ rawData

  return (
    <div className="glass-card vehicle-types-card">
      <div className="section-title">📊 Phân loại phương tiện · Tổng 3 làn</div>

      <div className="vtype-grid">
        {VEHICLE_DEFS.map(({ type, icon, label, color }) => {
          const count = counts[type] || 0;
          const pct   = rawData.length > 0
            ? ((count / total) * 100).toFixed(1)
            : '0.0';

          // per-lane breakdown
          const laneBreakdown = LANE_DEFS.map(({ dir, symbol, color: lc }) => ({
            symbol,
            color: lc,
            count: rawData.filter(
              d => (d.vehicle_type  || '').toLowerCase() === type
                && (d.direction     || '').toLowerCase() === dir
            ).length,
          }));

          return (
            <div
              key={type}
              className="vtype-item"
              style={{ position: 'relative', overflow: 'hidden' }}
            >
              {/* top accent bar */}
              <div style={{
                position: 'absolute', top: 0, left: 0, right: 0, height: 2,
                background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
                borderRadius: '2px 2px 0 0',
              }} />

              <div className="vtype-icon">{icon}</div>
              <div className="vtype-name">{label}</div>

              {/* animated count */}
              <div
                className="vtype-count"
                style={{ color, transition: 'all 0.3s ease' }}
              >
                {count}
              </div>
              <div className="vtype-pct">{pct}%</div>

              {/* progress bar */}
              <div style={{
                marginTop: 8, height: 4,
                background: 'rgba(255,255,255,0.07)',
                borderRadius: 2, overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%',
                  width: `${pct}%`,
                  background: `linear-gradient(90deg, ${color}88, ${color})`,
                  borderRadius: 2,
                  transition: 'width 0.5s ease',
                }} />
              </div>

              {/* per-lane mini */}
              <div style={{
                display: 'flex', gap: 4,
                marginTop: 10,
                justifyContent: 'center',
                padding: '6px 0 2px',
                borderTop: '1px solid var(--border)',
              }}>
                {laneBreakdown.map(({ symbol, color: lc, count: lc2 }) => (
                  <div key={symbol} style={{
                    display: 'flex', flexDirection: 'column',
                    alignItems: 'center', gap: 2, minWidth: 26,
                  }}>
                    <span style={{ fontSize: 10, color: lc, fontWeight: 700 }}>{symbol}</span>
                    <span style={{
                      fontSize: 12,
                      color: 'var(--text-2)',
                      fontFamily: 'JetBrains Mono, monospace',
                      fontWeight: 600,
                      transition: 'all 0.3s ease',
                    }}>{lc2}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
