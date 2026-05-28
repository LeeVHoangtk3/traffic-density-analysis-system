// LanePanel.js (Đóng vai trò ROI Traffic Flow Monitor)
// Phân phối chi tiết chủng loại phương tiện đi qua vùng ROI tổng thời gian thực

const VEHICLE_DEFS = [
  { type: 'car',        icon: '🚗', label: 'Ô tô',      color: '#3B82F6' },
  { type: 'motorcycle', icon: '🏍️', label: 'Xe máy',    color: '#10B981' },
  { type: 'truck',      icon: '🚛', label: 'Xe tải',     color: '#F59E0B' },
  { type: 'bus',        icon: '🚌', label: 'Xe buýt',    color: '#EF4444' },
];

export default function LanePanel({ rawData = [], aggregation }) {
  const total = rawData.length || 1;

  // Tính số lượng xe theo từng chủng loại
  const typeCounts = {};
  VEHICLE_DEFS.forEach(({ type }) => {
    typeCounts[type] = rawData.filter(
      d => (d.vehicle_type || '').toLowerCase() === type
    ).length;
  });

  return (
    <div className="glass-card lane-card" style={{ height: '100%', borderTop: '3px solid var(--primary)', padding: '20px 24px' }}>
      {/* Header */}
      <div className="lane-header" style={{ marginBottom: 16 }}>
        <div className="lane-title-row">
          <span style={{ fontSize: 24 }}>📊</span>
          <span className="lane-title" style={{ fontSize: 16, fontWeight: 700, letterSpacing: '0.05em' }}>
            PHÂN TÍCH CHỦNG LOẠI PHƯƠNG TIỆN (ROI FLOW)
          </span>
        </div>
        <span 
          style={{
            fontSize: 10, background: 'rgba(59,130,246,0.12)', border: '1px solid rgba(59,130,246,0.3)',
            color: '#60A5FA', padding: '3px 10px', borderRadius: 12, fontWeight: 700
          }}
        >
          ● ĐANG GIÁM SÁT
        </span>
      </div>

      <p style={{ color: 'var(--text-3)', fontSize: 13, marginBottom: 20, marginTop: -4 }}>
        Số liệu chi tiết phân bổ các loại phương tiện thu thập trực tiếp từ camera AI khi vượt qua mặt cắt ROI.
      </p>

      {/* Grid of Vehicles Breakdown */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: 16,
      }}>
        {VEHICLE_DEFS.map(({ type, icon, label, color }) => {
          const count = typeCounts[type] || 0;
          const pct = total > 1 ? Math.round((count / rawData.length) * 100) : 0;
          
          return (
            <div 
              key={type} 
              style={{
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid var(--border)',
                borderRadius: 12,
                padding: '16px 10px',
                textAlign: 'center',
                boxShadow: '0 4px 10px rgba(0,0,0,0.2)',
                position: 'relative',
                overflow: 'hidden'
              }}
            >
              <div style={{ fontSize: 24, marginBottom: 4 }}>{icon}</div>
              <div style={{
                fontSize: 10,
                color: 'var(--text-4)',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
              }}>{label}</div>
              
              <div style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 28,
                fontWeight: 800,
                color: 'var(--text-1)',
                marginTop: 8,
              }}>{count}</div>
              
              <div style={{ fontSize: 11, color: color, marginTop: 4, fontWeight: 700 }}>
                {pct}%
              </div>
              
              {/* Premium Progress Bar */}
              <div style={{
                marginTop: 10, height: 4,
                background: 'rgba(255,255,255,0.05)',
                borderRadius: 2, overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%',
                  width: `${pct}%`,
                  background: color,
                  borderRadius: 2,
                  boxShadow: `0 0 8px ${color}`,
                  transition: 'width 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
                }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
