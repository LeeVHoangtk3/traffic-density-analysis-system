import React, { useEffect, useState, useCallback, useMemo } from 'react';
import './App.css';

import Header          from './components/Header';
import TotalCard       from './components/TotalCard';
import VehicleTypes    from './components/VehicleTypes';
import LanePanel       from './components/LanePanel';
import VideoPanel      from './components/VideoPanel';
import HistoryChart    from './components/HistoryChart';
import PredictionPanel from './components/PredictionPanel';

const API = 'http://localhost:8000';

export default function App() {
  const [aggregation, setAggregation] = useState(null);
  const [rawData,     setRawData]     = useState([]);
  const [history,     setHistory]     = useState([]);
  const [prediction,  setPrediction]  = useState(null);
  const [videoTime,   setVideoTime]   = useState(0); // giây từ đầu video

  // ─── fetch helpers ───────────────────────────────────────────────
  const fetchAggregation = useCallback(async () => {
    try {
      const r = await fetch(`${API}/aggregation`);
      if (r.ok) setAggregation(await r.json());
    } catch {}
  }, []);

  const fetchRaw = useCallback(async () => {
    try {
      const r = await fetch(`${API}/raw-data?limit=2000`);
      if (r.ok) {
        const d = await r.json();
        setRawData(Array.isArray(d?.items) ? d.items : []);
      }
    } catch {}
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const r = await fetch(`${API}/aggregation/history?limit=60`);
      if (r.ok) {
        const d = await r.json();
        setHistory(Array.isArray(d?.items) ? d.items : []);
      }
    } catch {}
  }, []);

  const fetchPrediction = useCallback(async () => {
    try {
      const r = await fetch(`${API}/predict-next`);
      if (r.ok) setPrediction(await r.json());
    } catch {}
  }, []);

  // ─── initial load + polling ──────────────────────────────────────
  useEffect(() => {
    fetchAggregation();
    fetchRaw();
    fetchHistory();
    fetchPrediction();

    const t1 = setInterval(fetchAggregation, 5000);
    const t2 = setInterval(fetchRaw,         15000);
    const t3 = setInterval(fetchHistory,     10000);
    const t4 = setInterval(fetchPrediction,  30000);

    return () => [t1, t2, t3, t4].forEach(clearInterval);
  }, [fetchAggregation, fetchRaw, fetchHistory, fetchPrediction]);

  // ─── Video-time sync logic ───────────────────────────────────────
  // 1. Sắp xếp rawData tăng dần theo timestamp
  const sortedRaw = useMemo(() =>
    [...rawData].sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    ),
    [rawData]
  );

  // 2. Mốc t=0 của video = timestamp nhỏ nhất trong rawData
  const videoStartMs = useMemo(() =>
    sortedRaw.length > 0 ? new Date(sortedRaw[0].timestamp).getTime() : null,
    [sortedRaw]
  );

  // 3. filteredRaw: chỉ lấy xe detect TRONG khoảng [videoStartMs, videoStartMs + videoTime*1000)
  //    → tại t=0: 0 xe; tăng dần từng giây theo video
  const filteredRaw = useMemo(() => {
    if (!videoStartMs || !sortedRaw.length) return [];
    const cutoffMs = videoStartMs + videoTime * 1000;
    return sortedRaw.filter(d => {
      const ts = new Date(d.timestamp).getTime();
      return ts >= videoStartMs && ts < cutoffMs;
    });
  }, [sortedRaw, videoStartMs, videoTime]);

  return (
    <div className="app">
      <Header videoStartMs={videoStartMs} videoTime={videoTime} />

      <div className="main-grid">
        {/* ── Tổng số xe ── */}
        <div className="area-total">
          <TotalCard rawData={filteredRaw} aggregation={aggregation} />
        </div>

        {/* ── Phân loại xe ── */}
        <div className="area-vehicle-types">
          <VehicleTypes rawData={filteredRaw} />
        </div>

        {/* ── 3 làn ── */}
        <div className="area-lanes">
          <LanePanel rawData={filteredRaw} aggregation={aggregation} />
        </div>

        {/* ── Video ── */}
        <div className="area-video">
          <VideoPanel onTimeUpdate={setVideoTime} />
        </div>

        {/* ── Dự đoán ── */}
        <div className="area-predict">
          <PredictionPanel data={prediction} />
        </div>

        {/* ── Biểu đồ lịch sử — gốc = videoStartMs ── */}
        <div className="area-chart">
          <HistoryChart
            history={history}
            videoTime={videoTime}
            videoStartMs={videoStartMs}
          />
        </div>
      </div>
    </div>
  );
}