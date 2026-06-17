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


function fmtMs(ms) {
  if (!ms) return '';
  try {
    return new Date(ms).toLocaleTimeString('vi-VN', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  } catch { return ''; }
}

const verticalLinePlugin = {
  id: 'verticalLine',
  afterDraw: (chart) => {
    if (chart.tooltip?._active?.length) return;

    const { currentMs, processedHistory } = chart.config.options.plugins.verticalLine || {};
    if (!currentMs || !processedHistory || processedHistory.length === 0) return;

    const times = processedHistory.map(item => new Date(item.timestamp).getTime());
    const N = times.length;

    let x = null;
    if (currentMs <= times[0]) {
      x = chart.scales.x.getPixelForTick(0);
    } else if (currentMs >= times[N - 1]) {
      x = chart.scales.x.getPixelForTick(N - 1);
    } else {
      for (let i = 0; i < N - 1; i++) {
        const tStart = times[i];
        const tEnd = times[i + 1];
        if (currentMs >= tStart && currentMs <= tEnd) {
          const pStart = chart.scales.x.getPixelForTick(i);
          const pEnd = chart.scales.x.getPixelForTick(i + 1);
          const ratio = (currentMs - tStart) / (tEnd - tStart);
          x = pStart + ratio * (pEnd - pStart);
          break;
        }
      }
    }

    if (x === null || isNaN(x)) return;

    const ctx = chart.ctx;
    const topY = chart.chartArea.top;
    const bottomY = chart.chartArea.bottom;

    ctx.save();
    ctx.beginPath();
    ctx.moveTo(x, topY);
    ctx.lineTo(x, bottomY);
    ctx.strokeStyle = '#f97316'; // var(--orange)
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.stroke();

    // Circle at top
    ctx.beginPath();
    ctx.arc(x, topY, 4, 0, 2 * Math.PI);
    ctx.fillStyle = '#f97316';
    ctx.fill();

    // Circle at bottom
    ctx.beginPath();
    ctx.arc(x, bottomY, 4, 0, 2 * Math.PI);
    ctx.fillStyle = '#f97316';
    ctx.fill();

    ctx.restore();
  }
};

export default function HistoryChart({ historyData = [], currentMs, averageStats }) {
  const chartRef = useRef(null);

  // 1. Sắp xếp và Lọc dữ liệu: Nếu dữ liệu kéo dài hơn 6 tiếng, chỉ hiển thị 6 tiếng gần nhất
  const processedHistory = useMemo(() => {
    if (!historyData || !historyData.length) return [];

    const sorted = [...historyData].sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    const latestMs = new Date(sorted[sorted.length - 1].timestamp).getTime();
    const cutoffMs = latestMs - 6 * 60 * 60 * 1000; // Cửa sổ trượt 6 tiếng gần nhất

    return sorted.filter(item => new Date(item.timestamp).getTime() >= cutoffMs);
  }, [historyData]);





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
          color: '#f1f5f9',
          font: { size: 11, family: 'Inter, sans-serif' },
          boxWidth: 12,
          boxHeight: 12,
        },
      },
      tooltip: {
        backgroundColor: 'rgba(8,18,38,0.95)',
        titleColor: '#ffffff',
        bodyColor: '#f1f5f9',
        borderColor: 'rgba(255,255,255,0.15)',
        borderWidth: 1,
        padding: 12,
        titleFont: { size: 12, weight: '700', family: 'JetBrains Mono, monospace' },
        bodyFont: { size: 11 },
        callbacks: {
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              label += context.parsed.y.toLocaleString('en-US');
            }
            return label;
          }
        }
      },
      verticalLine: {
        currentMs,
        processedHistory
      }
    },
    scales: {
      x: {
        ticks: {
          color: '#cbd5e1',
          font: { size: 10, family: 'JetBrains Mono, monospace' },
          maxTicksLimit: 7,
          maxRotation: 0,
        },
        grid: { color: 'rgba(255,255,255,0.03)' },
        border: { color: 'rgba(255,255,255,0.05)' },
      },
      y: {
        beginAtZero: true,
        ticks: { 
          color: '#cbd5e1', 
          font: { size: 11 },
          callback: function(value) {
            return value.toLocaleString('en-US');
          }
        },
        grid: { color: 'rgba(255,255,255,0.04)' },
        border: { color: 'rgba(255,255,255,0.05)' },
        title: {
          display: true,
          text: 'Lượng phương tiện / 15 phút',
          color: '#94a3b8',
          font: { size: 10 },
        },
      },
    },
  };

  const startLabel = processedHistory.length > 0 ? fmtMs(new Date(processedHistory[0].timestamp).getTime()) : '--:--:--';
  const endLabel = processedHistory.length > 0 ? fmtMs(new Date(processedHistory[processedHistory.length - 1].timestamp).getTime()) : '--:--:--';

  const avgVehiclesStr = (averageStats && averageStats.average_vehicle_count !== undefined && averageStats.average_vehicle_count !== null)
    ? Number(averageStats.average_vehicle_count).toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
    : '--';

  const peakVehiclesStr = (averageStats && averageStats.peak_vehicle_count !== undefined && averageStats.peak_vehicle_count !== null)
    ? Number(averageStats.peak_vehicle_count).toLocaleString('en-US')
    : '--';

  return (
    <div className="glass-card chart-card">
      <div className="chart-header-row">
        <div className="chart-title-block">
          <div className="chart-title">📈 LỊCH SỬ MẬT ĐỘ TÍCH LŨY HỆ THỐNG</div>
          <div className="chart-subtitle">
            {processedHistory.length} điểm dữ liệu · Khung: {startLabel} - {endLabel} (6h gần nhất)
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
          <Line ref={chartRef} data={chartData} options={options} plugins={[verticalLinePlugin]} />
        </div>
      )}

      {/* Thống kê hiệu suất / Chỉ số trung bình & giờ cao điểm ở dưới biểu đồ lịch sử */}
      {averageStats && (
        <div style={{
          marginTop: 20,
          paddingTop: 16,
          borderTop: '1px solid var(--border)',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 16
        }}>
          <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border)', borderRadius: 12, padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ fontSize: 24 }}>📈</div>
            <div>
              <div style={{ fontSize: 10, color: 'var(--text-4)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 2 }}>
                Lưu lượng trung bình (15 phút)
              </div>
              <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-2)', fontFamily: 'JetBrains Mono, monospace' }}>
                {avgVehiclesStr}
                <span style={{ fontSize: 12, color: 'var(--text-3)', marginLeft: 4, fontWeight: 400 }}>xe / 15p</span>
              </div>
            </div>
          </div>
          
          <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border)', borderRadius: 12, padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ fontSize: 24 }}>🔥</div>
            <div>
              <div style={{ fontSize: 10, color: 'var(--text-4)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 2 }}>
                Giờ cao điểm nhất
              </div>
              <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--orange)', fontFamily: 'JetBrains Mono, monospace' }}>
                {averageStats.peak_hour}
                <span style={{ fontSize: 11, color: 'var(--text-3)', marginLeft: 8, fontWeight: 400 }}>
                  (Đạt {peakVehiclesStr} xe)
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
