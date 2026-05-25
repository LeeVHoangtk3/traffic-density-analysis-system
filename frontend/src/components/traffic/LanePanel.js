// LanePanel.js
// Tất cả đếm xe đều từ rawData (filteredRaw) → tăng dần theo video
// Congestion level dùng từ aggregation (BE tính)

const LEVEL_COLORS = {
  low:    { bg: 'var(--green-dim)',   border: 'rgba(16,185,129,0.3)',  text: 'var(--green)',  glow: 'rgba(16,185,129,0.15)' },
  medium: { bg: 'var(--yellow-dim)', border: 'rgba(245,158,11,0.3)',  text: 'var(--yellow)', glow: 'rgba(245,158,11,0.15)' },
  high:   { bg: 'var(--orange-dim)', border: 'rgba(249,115,22,0.3)',  text: 'var(--orange)', glow: 'rgba(249,115,22,0.15)' },
  heavy:  { bg: 'var(--red-dim)',    border: 'rgba(239,68,68,0.3)',   text: 'var(--red)',    glow: 'rgba(239,68,68,0.15)'  },
  severe: { bg: 'rgba(255,0,0,.1)',  border: 'rgba(255,0,0,0.35)',   text: '#ff3333',       glow: 'rgba(255,0,0,0.12)'   },
};

const LANES = [
  { dir: 'left',     label: 'LÀN TRÁI',  icon: '←', accentColor: '#10b981', textColor: '#34d399' },
  { dir: 'straight', label: 'LÀN THẲNG', icon: '↑', accentColor: '#f59e0b', textColor: '#fbbf24' },
  { dir: 'right',    label: 'LÀN PHẢI',  icon: '→', accentColor: '#ef4444', textColor: '#f87171' },
];

const VEHICLE_DEFS = [
  { type: 'car',        icon: '🚗', label: 'Ô tô'   },
  { type: 'motorcycle', icon: '🏍️', label: 'Xe máy' },
  { type: 'truck',      icon: '🚛', label: 'Xe tải' },
  { type: 'bus',        icon: '🚌', label: 'Xe buýt' },
];

function getLevelStyle(level = '') {
  return LEVEL_COLORS[(level || '').toLowerCase()] || LEVEL_COLORS.low;
}

function levelIcon(level = '') {
  const l = (level || '').toLowerCase();
  if (l === 'heavy' || l === 'severe') return '🔴';
  if (l === 'high')   return '🟠';
  if (l === 'medium') return '🟡';
  return '🟢';
}

export default function LanePanel({ rawData = [], aggregation }) {
  const cl = aggregation?.congestion_levels || {};

  return (
    <div className="lanes-container">
      {LANES.map(({ dir, label, icon, accentColor, textColor }) => {
        // ── Đếm từ rawData ──
        const laneItems = rawData.filter(
          d => (d.direction || '').toLowerCase() === dir
        );
        const count    = laneItems.length;
        const level    = cl[dir] ?? 'Low';
        const lvStyle  = getLevelStyle(level);
        const laneTotal = count || 1;

        // per vehicle type
        const typeCounts = {};
        VEHICLE_DEFS.forEach(({ type }) => {
          typeCounts[type] = laneItems.filter(
            d => (d.vehicle_type || '').toLowerCase() === type
          ).length;
        });

        return (
          <div
            key={dir}
            className="glass-card lane-card"
            style={{
              borderTop: `3px solid ${accentColor}`,
              boxShadow: `0 0 24px ${lvStyle.glow}, 0 4px 16px rgba(0,0,0,0.4)`,
            }}
          >
            {/* Header */}
            <div className="lane-header">
              <div className="lane-title-row">
                <span style={{ fontSize: 22 }}>{icon}</span>
                <span className="lane-title">{label}</span>
              </div>
              <span
                className="lane-congestion"
                style={{
                  background: lvStyle.bg,
                  color: lvStyle.text,
                  border: `1px solid ${lvStyle.border}`,
                }}
              >
                {levelIcon(level)} {level}
              </span>
            </div>

            {/* Big count */}
            <div className="lane-count-big" style={{ color: textColor }}>
              {count.toLocaleString()}
              <span style={{ fontSize: 14, color: 'var(--text-3)', marginLeft: 8, fontWeight: 400 }}>xe</span>
            </div>

            {/* Vehicle type breakdown */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: 8,
              marginTop: 6,
            }}>
              {VEHICLE_DEFS.map(({ type, icon: vIcon, label: vLabel }) => {
                const c   = typeCounts[type] || 0;
                const pct = count > 0 ? Math.round((c / laneTotal) * 100) : 0;
                return (
                  <div key={type} style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid var(--border)',
                    borderRadius: 8,
                    padding: '8px 6px',
                    textAlign: 'center',
                    transition: 'all 0.25s ease',
                  }}>
                    <div style={{ fontSize: 16 }}>{vIcon}</div>
                    <div style={{
                      fontSize: 9,
                      color: 'var(--text-4)',
                      marginTop: 2,
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                    }}>{vLabel}</div>
                    <div style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 18,
                      fontWeight: 700,
                      color: 'var(--text-1)',
                      marginTop: 4,
                      transition: 'all 0.3s ease',
                    }}>{c}</div>
                    <div style={{ fontSize: 9, color: accentColor, marginTop: 2, fontWeight: 600 }}>
                      {pct}%
                    </div>
                    {/* mini bar */}
                    <div style={{
                      marginTop: 5, height: 3,
                      background: 'rgba(255,255,255,0.06)',
                      borderRadius: 2, overflow: 'hidden',
                    }}>
                      <div style={{
                        height: '100%',
                        width: `${pct}%`,
                        background: accentColor,
                        borderRadius: 2,
                        transition: 'width 0.4s ease',
                      }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
