// PredictionPanel.js

function levelColor(level = '') {
  const l = level.toLowerCase();
  if (l === 'heavy' || l === 'severe') return 'var(--red)';
  if (l === 'high')   return 'var(--orange)';
  if (l === 'medium') return 'var(--yellow)';
  return 'var(--green)';
}

function levelIcon(level = '') {
  const l = (level || '').toLowerCase();
  if (l === 'heavy' || l === 'severe') return '🔴';
  if (l === 'high')   return '🟠';
  if (l === 'medium') return '🟡';
  return '🟢';
}

export default function PredictionPanel({ data }) {
  if (!data) {
    return (
      <div className="glass-card predict-card" style={{ height: '100%', justifyContent: 'center', alignItems: 'center' }}>
        <div style={{ textAlign: 'center', color: 'var(--text-4)' }}>
          <div style={{ fontSize: 36, marginBottom: 10 }}>🔮</div>
          <div style={{ fontSize: 13 }}>Đang tải dự đoán...</div>
        </div>
      </div>
    );
  }

  const {
    predicted_density,
    predicted_congestion_level,
    green_light_time,
    predictions,
    congestion_levels,
    phase_timing,
    horizon_minutes,
    source,
    timestamp,
  } = data;

  const pt = phase_timing || {};
  const preds = predictions || {};
  const maxPred = Math.max(preds.left || 0, preds.straight || 0, preds.right || 0, 1);

  const DIRS = [
    { key: 'left',     label: '← Trái',   color: '#10b981' },
    { key: 'straight', label: '↑ Thẳng',  color: '#f59e0b' },
    { key: 'right',    label: '→ Phải',   color: '#ef4444' },
  ];

  return (
    <div className="glass-card predict-card" style={{ height: '100%' }}>
      <div className="section-title">🔮 DỰ ĐOÁN · {horizon_minutes ?? 15} phút tới</div>

      {/* Predicted density */}
      <div className="predict-density-block">
        <div className="predict-density-label">Mật độ dự đoán</div>
        <div className="predict-density-value">{Math.round(predicted_density ?? 0)}</div>
        <div className="predict-density-unit">xe / cửa sổ</div>
        {predicted_congestion_level && (
          <div style={{
            marginTop: 8, display: 'inline-flex', alignItems: 'center', gap: 5,
            padding: '3px 12px', borderRadius: 20,
            background: 'rgba(168,85,247,0.15)',
            border: '1px solid rgba(168,85,247,0.3)',
            fontSize: 11, fontWeight: 700, color: levelColor(predicted_congestion_level),
          }}>
            {levelIcon(predicted_congestion_level)} {predicted_congestion_level}
          </div>
        )}
      </div>

      {/* Per-direction predictions */}
      <div>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-4)', marginBottom: 8 }}>
          Dự đoán theo làn
        </div>
        <div className="predict-directions">
          {DIRS.map(({ key, label, color }) => {
            const val = preds[key] || 0;
            const pct = Math.min(100, (val / maxPred) * 100);
            const lvl = congestion_levels?.[key];
            return (
              <div key={key} className="predict-dir-row">
                <div className="predict-dir-label" style={{ color }}>
                  {label}
                </div>
                <div className="predict-dir-bar-wrap">
                  <div className="predict-dir-bar" style={{ width: `${pct}%`, background: color }} />
                </div>
                <div className="predict-dir-count">{val}</div>
                {lvl && (
                  <span style={{
                    fontSize: 9, padding: '2px 6px', borderRadius: 10,
                    background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border)',
                    color: levelColor(lvl), fontWeight: 700, whiteSpace: 'nowrap',
                  }}>{lvl}</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Green light recommendation */}
      <div className="predict-green-block">
        <div className="predict-green-label">⏱ Đèn xanh đề xuất</div>
        <div className="predict-green-value">{green_light_time ?? 45}</div>
        <div className="predict-green-unit">giây</div>
      </div>

      {/* Phase timing */}
      {pt.phase_1_green !== undefined && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
          <div style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.15)', borderRadius: 8, padding: '8px 10px', textAlign: 'center' }}>
            <div style={{ fontSize: 9, color: 'var(--green)', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Pha 1 Xanh</div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 18, fontWeight: 700, color: 'var(--green)' }}>{pt.phase_1_green}s</div>
          </div>
          <div style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.15)', borderRadius: 8, padding: '8px 10px', textAlign: 'center' }}>
            <div style={{ fontSize: 9, color: 'var(--green)', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Pha 2 Xanh</div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 18, fontWeight: 700, color: 'var(--green)' }}>{pt.phase_2_green}s</div>
          </div>
        </div>
      )}

      <div className="predict-source">
        📡 {source} · {timestamp ? new Date(timestamp).toLocaleTimeString('vi-VN') : '--'}
      </div>
    </div>
  );
}
