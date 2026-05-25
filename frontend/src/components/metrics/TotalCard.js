// TotalCard.js
// Tổng số xe — tính từ rawData (filteredRaw) để tăng dần theo video
// Congestion level vẫn lấy từ aggregation (BE tính)

function levelClass(level = '') {
  return 'level-' + (level || 'low').toLowerCase();
}

function levelIcon(level = '') {
  const l = (level || '').toLowerCase();
  if (l === 'heavy' || l === 'severe') return '🔴';
  if (l === 'high')   return '🟠';
  if (l === 'medium') return '🟡';
  return '🟢';
}

export default function TotalCard({ rawData = [], aggregation }) {
  // ── Tính từ rawData đã filter theo videoTime ──────────────────────
  const total    = rawData.length;
  const left     = rawData.filter(d => (d.direction || '').toLowerCase() === 'left').length;
  const straight = rawData.filter(d => (d.direction || '').toLowerCase() === 'straight').length;
  const right    = rawData.filter(d => (d.direction || '').toLowerCase() === 'right').length;
  const inbound  = rawData.filter(d => (d.direction || '').toLowerCase() === 'inbound').length;

  // Congestion & queue từ aggregation endpoint
  const level      = aggregation?.congestion_level ?? '';
  const queueProxy = aggregation?.queue_proxy ?? 0;

  return (
    <div className="glass-card total-card">
      <div className="total-label">🚗 TỔNG SỐ PHƯƠNG TIỆN</div>

      {/* Big number */}
      <div className="total-number">{total.toLocaleString()}</div>

      {/* Direction breakdown */}
      <div className="total-sub">
        <div className="total-sub-item">
          <span className="total-sub-dot" style={{ background: '#10b981' }} />
          Trái: <strong style={{ color: '#f1f5f9', marginLeft: 4 }}>{left}</strong>
        </div>
        <div className="total-sub-item">
          <span className="total-sub-dot" style={{ background: '#f59e0b' }} />
          Thẳng: <strong style={{ color: '#f1f5f9', marginLeft: 4 }}>{straight}</strong>
        </div>
        <div className="total-sub-item">
          <span className="total-sub-dot" style={{ background: '#ef4444' }} />
          Phải: <strong style={{ color: '#f1f5f9', marginLeft: 4 }}>{right}</strong>
        </div>
      </div>

      {/* Inbound & Queue */}
      <div style={{ display: 'flex', gap: 12, marginTop: 2 }}>
        <div style={{ fontSize: 11, color: 'var(--text-3)', display: 'flex', alignItems: 'center', gap: 4 }}>
          📥 Inbound: <strong style={{ color: 'var(--text-2)', marginLeft: 4 }}>{inbound}</strong>
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-3)', display: 'flex', alignItems: 'center', gap: 4 }}>
          🔢 Queue: <strong style={{ color: 'var(--text-2)', marginLeft: 4 }}>{queueProxy}</strong>
        </div>
      </div>

      {/* Congestion badge */}
      {level && (
        <span className={`congestion-badge ${levelClass(level)}`}>
          {levelIcon(level)} {level}
        </span>
      )}

      {/* Fallback nếu chưa có data */}
      {total === 0 && (
        <div style={{ fontSize: 11, color: 'var(--text-4)', marginTop: 4 }}>
          ⏳ Đang chờ dữ liệu từ camera...
        </div>
      )}
    </div>
  );
}
