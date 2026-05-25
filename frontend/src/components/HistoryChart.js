// HistoryChart.js
// Lịch sử số xe theo thời gian — gốc = thời gian bắt đầu video
// Marker vàng đồng bộ với giây hiện tại của video

import { useMemo, useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale, LinearScale,
  PointElement, LineElement,
  Tooltip, Legend, Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale, LinearScale,
  PointElement, LineElement,
  Tooltip, Legend, Filler,
);

// ── helpers ────────────────────────────────────────────────────────
function getTs(item) {
  return new Date(item.timestamp || item.generated_at || item.end_time || 0).getTime();
}

function fmtLabel(ms) {
  if (!ms) return '';
  try {
    return new Date(ms).toLocaleTimeString('vi-VN', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  } catch { return ''; }
}

function fmtSecs(s) {
  const sec = Math.floor(s || 0);
  const m = Math.floor(sec / 60);
  const r = sec % 60;
  return `${String(m).padStart(2,'0')}:${String(r).padStart(2,'0')}`;
}

// ── vertical-line plugin ───────────────────────────────────────────
const videoMarkerPlugin = {
  id: 'videoMarker',
  afterDraw(chart, _, opts) {
    const { index } = opts;
    if (index == null || index < 0) return;
    const meta = chart.getDatasetMeta(0);
    const pt   = meta?.data?.[index];
    if (!pt) return;

    const { ctx, chartArea: { top, bottom } } = chart;
    const x = pt.x;

    // Line
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, bottom);
    ctx.lineWidth   = 2;
    ctx.strokeStyle = '#f59e0b';
    ctx.setLineDash([5, 4]);
    ctx.stroke();
    ctx.restore();

    // Label badge
    const lbl  = opts.label || '';
    ctx.save();
    ctx.font = 'bold 10px JetBrains Mono, monospace';
    const tw = ctx.measureText(lbl).width;
    const bx = Math.min(x - tw / 2 - 5, chart.chartArea.right - tw - 14);
    ctx.fillStyle = 'rgba(245,158,11,0.92)';
    ctx.beginPath();
    ctx.roundRect(bx, top - 20, tw + 10, 17, 4);
    ctx.fill();
    ctx.fillStyle = '#000';
    ctx.fillText(lbl, bx + 5, top - 6);
    ctx.restore();
  },
};

ChartJS.register(videoMarkerPlugin);

// ──────────────────────────────────────────────────────────────────
export default function HistoryChart({ history, videoTime, videoStartMs }) {
  const chartRef = useRef(null);

  // 1. Sắp xếp history theo thời gian
  const sorted = useMemo(() =>
    [...history].sort((a, b) => getTs(a) - getTs(b)),
    [history]
  );

  // 2. Gốc của chart = videoStartMs
  //    Chỉ hiển thị records từ videoStartMs đến videoStartMs + videoTime
  //    → chart "mọc" dần ra phải khi video chạy
  const visibleItems = useMemo(() => {
    if (!videoStartMs || !sorted.length) return sorted;
    const cutoffMs = videoStartMs + videoTime * 1000;
    return sorted.filter(item => {
      const ts = getTs(item);
      return ts >= videoStartMs && ts <= cutoffMs;
    });
  }, [sorted, videoStartMs, videoTime]);

  // 3. Tìm index marker (điểm gần nhất với videoTime trong visibleItems)
  const markerIndex = useMemo(() => {
    if (!visibleItems.length) return null;
    return visibleItems.length - 1; // luôn là điểm cuối cùng đang thấy
  }, [visibleItems]);

  const markerLabel = markerIndex != null && visibleItems[markerIndex]
    ? fmtLabel(getTs(visibleItems[markerIndex]))
    : '';

  // 4. Nếu chưa có dữ liệu trong khoảng visible, hiển thị thông báo
  // 5. Chart data
  const labels = visibleItems.map(item => fmtLabel(getTs(item)));

  const chartData = {
    labels,
    datasets: [
      {
        label: 'Tổng xe',
        data: visibleItems.map(i => i.vehicle_count || 0),
        borderColor: '#60a5fa',
        backgroundColor: 'rgba(96,165,250,0.10)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointHoverRadius: 6,
        borderWidth: 2,
      },
      {
        label: '← Trái',
        data: visibleItems.map(i => i.direction_counts?.left || 0),
        borderColor: '#10b981',
        backgroundColor: 'rgba(16,185,129,0.05)',
        tension: 0.4,
        pointRadius: 2,
        pointHoverRadius: 5,
        borderWidth: 1.5,
      },
      {
        label: '↑ Thẳng',
        data: visibleItems.map(i => i.direction_counts?.straight || 0),
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245,158,11,0.05)',
        tension: 0.4,
        pointRadius: 2,
        pointHoverRadius: 5,
        borderWidth: 1.5,
      },
      {
        label: '→ Phải',
        data: visibleItems.map(i => i.direction_counts?.right || 0),
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239,68,68,0.05)',
        tension: 0.4,
        pointRadius: 2,
        pointHoverRadius: 5,
        borderWidth: 1.5,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        labels: {
          color: '#94a3b8',
          font: { size: 11, family: 'Inter, sans-serif' },
          usePointStyle: true,
          pointStyleWidth: 8,
          padding: 16,
        },
      },
      tooltip: {
        backgroundColor: 'rgba(8,18,38,0.95)',
        titleColor: '#f1f5f9',
        bodyColor: '#94a3b8',
        borderColor: 'rgba(255,255,255,0.1)',
        borderWidth: 1,
        padding: 12,
        titleFont: { size: 12, weight: '700', family: 'JetBrains Mono, monospace' },
        bodyFont:  { size: 11 },
        callbacks: {
          afterBody(items) {
            const row = visibleItems[items[0]?.dataIndex];
            return row?.congestion_level ? [`Mật độ: ${row.congestion_level}`] : [];
          },
        },
      },
      videoMarker: {
        index: markerIndex,
        label: markerLabel,
      },
    },
    scales: {
      x: {
        ticks: {
          color: '#64748b',
          font: { size: 10, family: 'JetBrains Mono, monospace' },
          maxTicksLimit: 10,
          maxRotation: 30,
        },
        grid:   { color: 'rgba(255,255,255,0.04)' },
        border: { color: 'rgba(255,255,255,0.06)' },
      },
      y: {
        beginAtZero: true,
        ticks: { color: '#64748b', font: { size: 11 } },
        grid:   { color: 'rgba(255,255,255,0.05)' },
        border: { color: 'rgba(255,255,255,0.06)' },
        title: {
          display: true,
          text: 'Số phương tiện',
          color: '#475569',
          font: { size: 10 },
        },
      },
    },
  };

  // Thông tin ref
  const startLabel = videoStartMs ? fmtLabel(videoStartMs) : '--:--:--';
  const currentLabel = videoStartMs
    ? fmtLabel(videoStartMs + videoTime * 1000)
    : '--:--:--';

  return (
    <div className="glass-card chart-card">
      <div className="chart-header-row">
        <div className="chart-title-block">
          <div className="chart-title">📈 LỊCH SỬ PHƯƠNG TIỆN THEO THỜI GIAN</div>
          <div className="chart-subtitle">
            {visibleItems.length} điểm dữ liệu · Gốc: {startLabel} · Cập nhật mỗi 10 giây
          </div>
        </div>

        {/* Video time info */}
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          {videoStartMs && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '6px 14px',
              background: 'rgba(245,158,11,0.10)',
              border: '1px solid rgba(245,158,11,0.25)',
              borderRadius: 8,
              fontSize: 11, color: '#f59e0b',
            }}>
              <span>🎬</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                Video {fmtSecs(videoTime)}
              </span>
              <span style={{ opacity: 0.6 }}>→</span>
              <strong style={{ fontFamily: 'JetBrains Mono, monospace' }}>{currentLabel}</strong>
              {visibleItems.length > 0 && (
                <>
                  <span style={{ opacity: 0.6 }}>·</span>
                  <span>{visibleItems[visibleItems.length - 1]?.vehicle_count ?? 0} xe</span>
                </>
              )}
            </div>
          )}

          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--text-2)' }}>
              <div style={{ width: 20, height: 2, background: '#f59e0b', borderTop: '2px dashed #f59e0b' }} />
              <span>Vị trí video</span>
            </div>
          </div>
        </div>
      </div>

      {/* Empty state — khi video chưa có data trong khoảng này */}
      {!visibleItems.length ? (
        <div className="chart-empty">
          <div className="chart-empty-icon">📊</div>
          <div style={{ color: 'var(--text-3)' }}>
            {!videoStartMs
              ? 'Đang chờ dữ liệu...'
              : `Chưa có dữ liệu tổng hợp từ ${startLabel}`}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-4)', marginTop: 4 }}>
            Dữ liệu sẽ hiện khi video chạy tới mốc có ghi nhận
          </div>
        </div>
      ) : (
        <div className="chart-box">
          <Line ref={chartRef} data={chartData} options={options} />
        </div>
      )}
    </div>
  );
}
