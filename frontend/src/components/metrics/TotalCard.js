// TotalCard.js
// Hiển thị tổng lượng xe đếm đơn ROI hợp nhất tích lũy thời gian thực

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

function levelTranslation(level = '') {
  const l = (level || '').toUpperCase();
  if (l === 'HEAVY' || l === 'SEVERE') return 'ÙN TẮC NGHIÊM TRỌNG';
  if (l === 'HIGH') return 'BẮT ĐẦU ĐÔNG XE';
  if (l === 'MEDIUM') return 'THÔNG THOÁNG';
  return 'ĐƯỜNG VẮNG';
}

export default function TotalCard({ rawData = [], aggregation, averageStats }) {
  // Lấy tổng số xe đã đếm qua ROI tổng
  const total = rawData.length;

  // Trạng thái mật độ tổng thể từ K-Means thích ứng
  const level = aggregation?.congestion_level ?? 'LOW';

  return (
    <div className="glass-card total-card" style={{ position: 'relative', overflow: 'hidden' }}>
      {/* Hiệu ứng nền nhẹ tinh tế */}
      <div style={{
        position: 'absolute', top: -50, right: -50, width: 120, height: 120,
        background: 'radial-gradient(circle, rgba(96,165,250,0.1) 0%, transparent 70%)',
        pointerEvents: 'none'
      }} />

      <div className="total-label" style={{ letterSpacing: '0.08em', fontWeight: 700 }}>
        🟢 ROI ĐẾM TỔNG HỢP NHẤT
      </div>

      {/* Số xe hiển thị cực đại */}
      <div className="total-number" style={{ fontSize: 56, letterSpacing: '-0.02em', margin: '10px 0' }}>
        {total.toLocaleString()}
        <span style={{ fontSize: 16, color: 'var(--text-3)', marginLeft: 8, fontWeight: 400 }}>phương tiện</span>
      </div>

      {/* Trạng thái mật độ động từ K-Means thích ứng */}
      <div style={{ marginTop: 8 }}>
        <div style={{ fontSize: 10, color: 'var(--text-4)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
          Mật độ thời gian thực (K-Means)
        </div>
        <span 
          className={`congestion-badge ${levelClass(level)}`}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '4px 14px', borderRadius: 20, fontSize: 12, fontWeight: 800
          }}
        >
          {levelIcon(level)} {levelTranslation(level)} ({level.toUpperCase()})
        </span>
      </div>

      {/* Chỉ số tích lũy từ Backend */}
      {averageStats && (
        <div style={{
          marginTop: 20,
          paddingTop: 16,
          borderTop: '1px solid var(--border)',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 12
        }}>
          <div>
            <div style={{ fontSize: 9, color: 'var(--text-4)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
              📈 Trung bình tích lũy
            </div>
            <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-2)', fontFamily: 'JetBrains Mono, monospace' }}>
              {averageStats.average_vehicle_count}
              <span style={{ fontSize: 10, color: 'var(--text-3)', marginLeft: 4, fontWeight: 400 }}>xe/15p</span>
            </div>
          </div>
          <div>
            <div style={{ fontSize: 9, color: 'var(--text-4)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
              🔥 Giờ cao điểm nhất
            </div>
            <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--orange)', fontFamily: 'JetBrains Mono, monospace' }}>
              {averageStats.peak_hour}
              <span style={{ fontSize: 9, color: 'var(--text-3)', display: 'block', fontWeight: 400, marginTop: 2 }}>
                (Đạt {averageStats.peak_vehicle_count} xe)
              </span>
            </div>
          </div>
        </div>
      )}

      {total === 0 && !averageStats && (
        <div style={{ fontSize: 11, color: 'var(--text-4)', marginTop: 8 }}>
          ⏳ Đang kết nối camera AI, vui lòng phát video...
        </div>
      )}
    </div>
  );
}
