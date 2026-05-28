// HistoryChart.js
// Vẽ lịch sử số xe tổng cộng vượt ROI theo chuỗi thời gian

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

const BIN_SECONDS = 10; // nhóm mỗi 10 giây

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

function buildBins(sortedRaw, videoStartMs, cutoffMs) {
  if (!sortedRaw.length || !videoStartMs) return [];

  const endMs = Math.min(
    cutoffMs,
    new Date(sortedRaw[sortedRaw.length - 1].timestamp).getTime() + BIN_SECONDS * 1000
  );
  const bins = [];

  for (let t = videoStartMs; t < endMs; t += BIN_SECONDS * 1000) {
    const binEnd = t + BIN_SECONDS * 1000;
    let total = 0;

    for (const item of sortedRaw) {
      const ts = new Date(item.timestamp).getTime();
      if (ts < videoStartMs) continue;
      if (ts >= binEnd) break;
      total++;
    }

    bins.push({
      time: binEnd,
      label: fmtMs(binEnd),
      total,
    });
  }

  return bins;
}

export default function HistoryChart({ sortedRaw, videoStartMs, videoTime }) {
  const chartRef = useRef(null);
  const cutoffMs = videoStartMs ? videoStartMs + videoTime * 1000 : 0;

  const allBins = useMemo(
    () => buildBins(sortedRaw, videoStartMs, new Date(sortedRaw[sortedRaw.length - 1]?.timestamp).getTime() + BIN_SECONDS * 1000),
    [sortedRaw, videoStartMs]
  );

  const visibleBins = useMemo(
    () => allBins.filter(b => b.time <= cutoffMs + BIN_SECONDS * 1000),
    [allBins, cutoffMs]
  );

  const markerIndex = visibleBins.length > 0 ? visibleBins.length - 1 : null;
  const markerLabel = markerIndex != null ? visibleBins[markerIndex].label : '';

  const chartData = {
    labels: visibleBins.map(b => b.label),
    datasets: [
      {
        label: 'Tổng số xe vượt ROI',
        data: visibleBins.map(b => b.total),
        borderColor: '#3B82F6',
        backgroundColor: 'rgba(59,130,246,0.06)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointHoverRadius: 6,
        borderWidth: 2.5,
      }
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 250 },
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
        label: markerLabel,
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
          text: 'Số lượng xe (lũy kế)',
          color: '#475569',
          font: { size: 10 },
        },
      },
    },
  };

  const startLabel = videoStartMs ? fmtMs(videoStartMs) : '--:--:--';
  const currentLabel = cutoffMs ? fmtMs(cutoffMs) : '--:--:--';

  return (
    <div className="glass-card chart-card">
      <div className="chart-header-row">
        <div className="chart-title-block">
          <div className="chart-title">📈 LỊCH SỬ LƯU LƯỢNG XE TỔNG HỢP</div>
          <div className="chart-subtitle">
            {visibleBins.length} điểm · Gốc: {startLabel} · Chu kỳ {BIN_SECONDS}s / điểm
          </div>
        </div>

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
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--text-3)' }}>
            <div style={{ width: 20, height: 2, background: '#f59e0b', borderTop: '2px dashed #f59e0b' }} />
            <span>Vị trí video</span>
          </div>
        </div>
      </div>

      {!visibleBins.length ? (
        <div className="chart-empty">
          <div className="chart-empty-icon">📊</div>
          <div style={{ color: 'var(--text-3)' }}>
            {!videoStartMs ? 'Đang chờ dữ liệu...' : 'Bắt đầu phát video để xem biểu đồ'}
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
