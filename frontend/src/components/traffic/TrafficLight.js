// TrafficLight.js — shows traffic light phase status from BE

function fmtTime(dt) {
  if (!dt) return '--';
  try {
    return new Date(dt).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch { return '--'; }
}

const PHASE_LABELS = {
  phase_1: { name: 'PHA 1', directions: ['straight', 'right'], dirLabels: ['↑ Thẳng', '→ Phải'] },
  phase_2: { name: 'PHA 2', directions: ['left'],              dirLabels: ['← Trái'] },
};

export default function TrafficLight({ data }) {
  if (!data) {
    return (
      <div className="glass-card traffic-light-card" style={{ height: '100%' }}>
        <div className="section-title">🚦 ĐÈN GIAO THÔNG</div>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-4)', fontSize: 13 }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>🚦</div>
            <div>Đang tải...</div>
          </div>
        </div>
      </div>
    );
  }

  const {
    camera_id, active_phase, cycle_time, transition_time,
    phase_timing, phases, mode, updated_at,
  } = data;

  const pt = phase_timing || {};

  const renderLight = (status) => {
    const s = (status || '').toUpperCase();
    return (
      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
        <div className={`tl-light ${s === 'RED'    ? 'red-on'    : ''}`} title="Red"    />
        <div className={`tl-light ${s === 'YELLOW' ? 'yellow-on' : ''}`} title="Yellow" />
        <div className={`tl-light ${s === 'GREEN'  ? 'green-on'  : ''}`} title="Green"  />
      </div>
    );
  };

  return (
    <div className="glass-card traffic-light-card" style={{ height: '100%' }}>
      <div className="section-title">🚦 ĐÈN GIAO THÔNG</div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="tl-camera">{camera_id}</span>
        <span className="tl-mode-badge">⚡ {mode}</span>
      </div>

      {/* Phases */}
      <div className="tl-phases">
        {['phase_1', 'phase_2'].map(phaseKey => {
          const phaseData  = phases?.[phaseKey] || {};
          const isActive   = active_phase === phaseKey;
          const status     = phaseData.status || 'RED';
          const duration   = phaseData.duration ?? (phaseKey === 'phase_1' ? pt.phase_1_green : pt.phase_2_green);
          const name       = phaseData.name || PHASE_LABELS[phaseKey]?.name;
          const dirList    = phaseData.directions || PHASE_LABELS[phaseKey]?.directions || [];

          return (
            <div key={phaseKey} className={`tl-phase ${isActive ? 'active' : ''}`}>
              <div className="tl-phase-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {isActive && (
                    <span style={{ width: 6, height: 6, background: 'var(--green)', borderRadius: '50%', animation: 'pulse-dot 1.4s ease infinite', display: 'inline-block' }} />
                  )}
                  <span className="tl-phase-name">{PHASE_LABELS[phaseKey]?.name} · {name}</span>
                </div>
                <span
                  className="tl-status-pill"
                  style={{
                    background: status === 'GREEN' ? 'var(--green-dim)' : status === 'YELLOW' ? 'var(--yellow-dim)' : 'var(--red-dim)',
                    color:      status === 'GREEN' ? 'var(--green)'     : status === 'YELLOW' ? 'var(--yellow)'     : 'var(--red)',
                    border:     `1px solid ${status === 'GREEN' ? 'rgba(16,185,129,0.3)' : status === 'YELLOW' ? 'rgba(245,158,11,0.3)' : 'rgba(239,68,68,0.3)'}`,
                  }}
                >
                  {status}
                </span>
              </div>

              {/* Traffic light visual */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                {renderLight(status)}
                <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 22, fontWeight: 700, color: 'var(--text-1)' }}>
                  {duration}<span style={{ fontSize: 11, color: 'var(--text-3)', marginLeft: 2 }}>s</span>
                </div>
              </div>

              {/* Directions */}
              <div className="tl-direction-chips">
                {dirList.map(d => (
                  <span key={d} className="tl-dir-chip">
                    {d === 'left' ? '← Trái' : d === 'right' ? '→ Phải' : '↑ Thẳng'}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Timing summary */}
      <div>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-4)', marginBottom: 8 }}>
          Thời gian pha
        </div>
        <div className="tl-timing-grid">
          <div className="tl-timing-item">
            <div className="tl-timing-label">Chu kỳ</div>
            <div className="tl-timing-value">{cycle_time}<span className="tl-timing-unit">s</span></div>
          </div>
          <div className="tl-timing-item">
            <div className="tl-timing-label">Chuyển pha</div>
            <div className="tl-timing-value">{transition_time}<span className="tl-timing-unit">s</span></div>
          </div>
          <div className="tl-timing-item">
            <div className="tl-timing-label">Pha 1 xanh</div>
            <div className="tl-timing-value" style={{ color: 'var(--green)' }}>{pt.phase_1_green}<span className="tl-timing-unit">s</span></div>
          </div>
          <div className="tl-timing-item">
            <div className="tl-timing-label">Pha 2 xanh</div>
            <div className="tl-timing-value" style={{ color: 'var(--green)' }}>{pt.phase_2_green}<span className="tl-timing-unit">s</span></div>
          </div>
        </div>
      </div>

      {/* Delta */}
      {(pt.delta_phase_1 !== 0 || pt.delta_phase_2 !== 0) && (
        <div style={{ display: 'flex', gap: 8 }}>
          {[
            { label: 'Δ Pha 1', val: pt.delta_phase_1 },
            { label: 'Δ Pha 2', val: pt.delta_phase_2 },
          ].map(({ label, val }) => (
            <div key={label} style={{
              flex: 1, padding: '6px 10px', borderRadius: 8,
              background: val > 0 ? 'var(--red-dim)' : val < 0 ? 'var(--green-dim)' : 'rgba(255,255,255,0.03)',
              border: '1px solid var(--border)',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: 9, color: 'var(--text-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
              <div style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 16, fontWeight: 700,
                color: val > 0 ? 'var(--red)' : val < 0 ? 'var(--green)' : 'var(--text-2)',
              }}>
                {val > 0 ? `+${val}` : val}s
              </div>
            </div>
          ))}
        </div>
      )}

      {updated_at && (
        <div style={{ fontSize: 10, color: 'var(--text-4)', fontFamily: 'JetBrains Mono, monospace', textAlign: 'center' }}>
          Updated {fmtTime(updated_at)}
        </div>
      )}
    </div>
  );
}
