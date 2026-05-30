// HistoryChart.js
// Vẽ toàn bộ lịch sử lượng xe tổng hợp thực tế tích lũy từ database (Giới hạn 12 tiếng gần nhất)
// Ghim vị trí phát video bằng thước đo dọc màu cam chuyển động đồng bộ.

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

const videoMarkerPlugin = {
  id: 'videoMarker',
  afterDraw(chart, _, opts) {
    const { index } = opts;
    if (index == null || index < 0) return;
    const meta = chart.getDatasetMeta(0);
    const pt = meta?.data?.[index];
    if (!pt) return;
    const { ctx, chartArea: { top, bottom, right } } = chart;
    const x = pt.x;

    ctx.save();
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, bottom);
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#f59e0b';
    ctx.setLineDash([5, 4]);
    ctx.stroke();
    ctx.restore();

    // Vẽ điểm tròn phát sáng (Glow Dot) tại giao điểm đồ thị (x, y) để nhận diện rõ điểm hiện tại
    const y = pt.y;
    ctx.save();
    // Halo phát sáng bên ngoài
    ctx.beginPath();
    ctx.arc(x, y, 12, 0, 2 * Math.PI);
    ctx.fillStyle = 'rgba(245, 158, 11, 0.35)';
    ctx.fill();
    // Điểm tròn cam chính giữa
    ctx.beginPath();
    ctx.arc(x, y, 6, 0, 2 * Math.PI);
    ctx.fillStyle = '#f59e0b';
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.fill();
    ctx.stroke();
    ctx.restore();

    const lbl = opts.label || '';
    ctx.save();
    ctx.font = 'bold 10px JetBrains Mono, monospace';
    const tw = ctx.measureText(lbl).width;
    const bx = Math.min(x - tw / 2 - 5, right - tw - 14);
    ctx.fillStyle = 'rgba(245,158,11,0.92)';
    ctx.beginPath();
    ctx.roundRect(Math.max(bx, chart.chartArea.left), top - 20, tw + 10, 17, 4);
    ctx.fill();
    ctx.fillStyle = '#000';
    ctx.fillText(lbl, Math.max(bx, chart.chartArea.left) + 5, top - 6);
    ctx.restore();
  },
};

ChartJS.register(videoMarkerPlugin);

function fmtMs(ms) {
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
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`;
}

export default function HistoryChart({ historyData = [], videoStartMs, videoTime, videoDuration }) {
  const chartRef = useRef(null);

  // 1. Sắp xếp và Lọc dữ liệu: Nếu dữ liệu kéo dài hơn 12 tiếng, chỉ hiển thị 12 tiếng gần nhất
  const processedHistory = useMemo(() => {
    if (!historyData || !historyData.length) return [];

    const sorted = [...historyData].sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    const latestMs = new Date(sorted[sorted.length - 1].timestamp).getTime();
    const cutoffMs = latestMs - 12 * 60 * 60 * 1000; // Cửa sổ trượt 12 tiếng gần nhất

    return sorted.filter(item => new Date(item.timestamp).getTime() >= cutoffMs);
  }, [historyData]);

  // 2. Tìm index của mốc thời gian phát video hiện tại trên đồ thị
  const markerIndex = useMemo(() => {
    if (!processedHistory.length || !videoStartMs || !videoDuration) return null;

    // Tìm virtual duration dựa trên mốc dữ liệu
    const firstDetMs = videoStartMs;
    const lastDetMs = new Date(processedHistory[processedHistory.length - 1].timestamp).getTime();
    const virtualDurationMs = Math.max(0, lastDetMs - firstDetMs);

    let scale = 1.0;
    if (videoDuration > 0 && virtualDurationMs > 0) {
      scale = (virtualDurationMs / 1000) / videoDuration;
    }

    const indicatorMs = firstDetMs + videoTime * scale * 1000;

    // Tìm điểm gần nhất trong processedHistory
    let closestIndex = 0;
    let minDiff = Infinity;

    processedHistory.forEach((item, idx) => {
      const ts = new Date(item.timestamp).getTime();
      const diff = Math.abs(ts - indicatorMs);
      if (diff < minDiff) {
        minDiff = diff;
        closestIndex = idx;
      }
    });

    return closestIndex;
  }, [processedHistory, videoStartMs, videoTime, videoDuration]);

  const markerLabel = useMemo(() => {
    if (markerIndex == null || !processedHistory[markerIndex]) return '';
    return fmtMs(new Date(processedHistory[markerIndex].timestamp).getTime());
  }, [processedHistory, markerIndex]);

  const chartData = {
    labels: processedHistory.map(item => {
      const t = new Date(item.timestamp);
      return t.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
    }),
    datasets: [
      {
        label: 'Lưu lượng thực tế (15p/chu kỳ)',
        data: processedHistory.map(item => item.vehicle_count),
        borderColor: '#3B82F6',
        backgroundColor: 'rgba(59,130,246,0.06)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 7,
        borderWidth: 2.5,
      }
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 200 },
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        labels: {
          color: '#94a3b8',
          font: { size: 11, family: 'Inter, sans-serif' },
          usePointStyle: true,
          pointStyleWidth: 8,
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
        bodyFont: { size: 11 },
      },
      videoMarker: {
        index: markerIndex,
        label: `🎬 Video đang chạy: ${markerLabel}`,
      },
    },
    scales: {
      x: {
        ticks: {
          color: '#64748b',
          font: { size: 10, family: 'JetBrains Mono, monospace' },
          maxTicksLimit: 12,
          maxRotation: 30,
        },
        grid: { color: 'rgba(255,255,255,0.03)' },
        border: { color: 'rgba(255,255,255,0.05)' },
      },
      y: {
        beginAtZero: true,
        ticks: { color: '#64748b', font: { size: 11 } },
        grid: { color: 'rgba(255,255,255,0.04)' },
        border: { color: 'rgba(255,255,255,0.05)' },
        title: {
          display: true,
          text: 'Lượng phương tiện / 15 phút',
          color: '#475569',
          font: { size: 10 },
        },
      },
    },
  };

  const startLabel = processedHistory.length > 0 ? fmtMs(new Date(processedHistory[0].timestamp).getTime()) : '--:--:--';
  const endLabel = processedHistory.length > 0 ? fmtMs(new Date(processedHistory[processedHistory.length - 1].timestamp).getTime()) : '--:--:--';

  return (
    <div className="glass-card chart-card">
      <div className="chart-header-row">
        <div className="chart-title-block">
          <div className="chart-title">📈 LỊCH SỬ MẬT ĐỘ TÍCH LŨY HỆ THỐNG</div>
          <div className="chart-subtitle">
            {processedHistory.length} điểm dữ liệu · Khung: {startLabel} - {endLabel} (12h gần nhất)
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          {videoStartMs && markerLabel && (
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
              <strong style={{ fontFamily: 'JetBrains Mono, monospace' }}>{markerLabel}</strong>
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--text-3)' }}>
            <div style={{ width: 20, height: 2, background: '#f59e0b', borderTop: '2px dashed #f59e0b' }} />
            <span>Điểm trùng khớp Video</span>
          </div>
        </div>
      </div>

      {!processedHistory.length ? (
        <div className="chart-empty">
          <div className="chart-empty-icon">📊</div>
          <div style={{ color: 'var(--text-3)' }}>
            Đang chờ dữ liệu lịch sử tích lũy từ database...
          </div>
        </div>
      ) : (
        <div className="chart-box" style={{ height: '240px' }}>
          <Line ref={chartRef} data={chartData} options={options} />
        </div>
      )}
    </div>
  );
}
