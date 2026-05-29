// PredictionPanel.js
// Hiển thị kết quả dự đoán và phân cụm mật độ tự thích ứng thế hệ mới (XGBoost + K-Means)

function levelColor(level = '') {
  const l = level.toUpperCase();
  if (l === 'HEAVY' || l === 'SEVERE') return '#EF4444'; // Đỏ rực rỡ
  if (l === 'HIGH')   return '#F59E0B'; // Vàng hổ phách
  if (l === 'MEDIUM') return '#3B82F6'; // Xanh hoàng gia
  return '#10B981'; // Xanh lục bảo
}

function levelIcon(level = '') {
  const l = level.toUpperCase();
  if (l === 'HEAVY' || l === 'SEVERE') return '🔴';
  if (l === 'HIGH')   return '🟠';
  if (l === 'MEDIUM') return '🟡';
  return '🟢';
}

function levelTranslation(level = '') {
  const l = level.toUpperCase();
  if (l === 'HEAVY' || l === 'SEVERE') return 'ÙN TẮC';
  if (l === 'HIGH')   return 'BẮT ĐẦU ĐÔNG';
  if (l === 'MEDIUM') return 'THÔNG THOÁNG';
  return 'ĐƯỜNG VẮNG';
}

export default function PredictionPanel({ data }) {
  if (!data) {
    return (
      <div className="glass-card predict-card" style={{ height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <div style={{ textAlign: 'center', color: 'var(--text-4)' }}>
          <div style={{ fontSize: 40, marginBottom: 10, animation: 'pulse 1.5s infinite' }}>🔮</div>
          <div style={{ fontSize: 13, fontWeight: 500 }}>Đang nạp mô hình dự báo XGBoost...</div>
        </div>
      </div>
    );
  }

  // Khai thác dữ liệu từ API v1 mới hoặc fallback tương thích cũ
  const predictedVolume = data.predicted_raw_volume ?? Math.round(data.predicted_density ?? 0);
  const statusLabel = data.status_label ?? data.predicted_congestion_level ?? 'LOW';
  const color = data.color_hex ?? levelColor(statusLabel);
  const timestamp = data.timestamp;
  const features = data.features_used || data.features || {};

  // Ma trận ngưỡng K-Means chuẩn
  const T1 = 94.81;
  const T2 = 199.54;
  const T3 = 369.01;

  // Tính tỷ lệ phần trăm thanh đo
  const maxScale = 500;
  const gaugePercent = Math.min(100, (predictedVolume / maxScale) * 100);

  return (
    <div className="glass-card predict-card" style={{ height: '100%', padding: '20px 24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
      <div>
        {/* Title */}
        <div className="section-title" style={{ fontSize: 14, fontWeight: 700, letterSpacing: '0.08em', marginBottom: 16 }}>
          🔮 TIÊN TRI AI · 15 PHÚT TỚI
        </div>

        {/* Prediction Main Block */}
        <div className="predict-density-block" style={{ textAlign: 'center', padding: '16px 0', background: 'rgba(255,255,255,0.01)', borderRadius: 12, border: '1px solid var(--border)', marginBottom: 20 }}>
          <div className="predict-density-label" style={{ fontSize: 11, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Lưu lượng dự báo (XGBoost)
          </div>
          <div className="predict-density-value" style={{ fontSize: 52, fontWeight: 800, color: color, fontFamily: 'JetBrains Mono, monospace', margin: '4px 0' }}>
            {predictedVolume}
          </div>
          <div className="predict-density-unit" style={{ fontSize: 12, color: 'var(--text-3)' }}>
            phương tiện / 15 phút
          </div>
          
          <div style={{
            marginTop: 10, display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '4px 14px', borderRadius: 20,
            background: 'rgba(255,255,255,0.03)',
            border: `1px solid ${color}`,
            fontSize: 12, fontWeight: 800, color: color
          }}>
            {levelIcon(statusLabel)} MẬT ĐỘ: {levelTranslation(statusLabel)} ({statusLabel})
          </div>
        </div>

        {/* K-Means Adaptive Gauge */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-4)', marginBottom: 10 }}>
            Thang phân cụm thích ứng (K-Means)
          </div>
          
          {/* Progress bar */}
          <div style={{ height: 8, background: 'rgba(255,255,255,0.05)', borderRadius: 4, position: 'relative', marginBottom: 8, overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: `${gaugePercent}%`,
              background: `linear-gradient(90deg, #10B981 0%, ${color} 100%)`,
              borderRadius: 4,
              boxShadow: `0 0 10px ${color}`,
              transition: 'width 0.6s cubic-bezier(0.4, 0, 0.2, 1)'
            }} />
          </div>

          {/* Threshold markers */}
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-4)' }}>
            <span>LOW ({Math.round(T1)}xe)</span>
            <span>MEDIUM ({Math.round(T2)}xe)</span>
            <span>HIGH ({Math.round(T3)}xe)</span>
            <span>HEAVY</span>
          </div>
        </div>
      </div>

      {/* Live Feature Engineering Monitor */}
      {features.lag_1 !== undefined && (
        <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border)', borderRadius: 12, padding: '12px 14px', marginBottom: 16 }}>
          <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-4)', marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
            <span>🖥️ Giám sát đặc trưng (Online Features)</span>
            <span style={{ color: 'var(--green)', fontWeight: 800 }}>● Live</span>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, textAlign: 'center' }}>
            <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: 8, padding: '6px 4px' }}>
              <div style={{ fontSize: 8, color: 'var(--text-4)', textTransform: 'uppercase' }}>lag_1 (t-15p)</div>
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, fontWeight: 700, color: 'var(--text-2)', marginTop: 2 }}>{Math.round(features.lag_1)}</div>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: 8, padding: '6px 4px' }}>
              <div style={{ fontSize: 8, color: 'var(--text-4)', textTransform: 'uppercase' }}>lag_2 (t-30p)</div>
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, fontWeight: 700, color: 'var(--text-2)', marginTop: 2 }}>{Math.round(features.lag_2)}</div>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: 8, padding: '6px 4px' }}>
              <div style={{ fontSize: 8, color: 'var(--text-4)', textTransform: 'uppercase' }}>rolling_mean</div>
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, fontWeight: 700, color: 'var(--text-2)', marginTop: 2 }}>{Math.round(features.rolling_mean_3)}</div>
            </div>
          </div>
        </div>
      )}

      {/* Footer Timestamp */}
      <div className="predict-source" style={{ fontSize: 10, display: 'flex', justifyContent: 'space-between', color: 'var(--text-4)', borderTop: '1px solid var(--border)', paddingTop: 10 }}>
        <span>🤖 XGBoost v1 Hợp nhất</span>
        <span>🕒 {timestamp ? new Date(timestamp).toLocaleTimeString('vi-VN') : '--'}</span>
      </div>
    </div>
  );
}
