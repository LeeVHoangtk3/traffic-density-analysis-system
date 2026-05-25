import React, { useEffect, useState, useCallback, useMemo } from 'react';
import './App.css';

import Header          from './components/layout/Header';
import TotalCard       from './components/metrics/TotalCard';
import VehicleTypes    from './components/metrics/VehicleTypes';
import LanePanel       from './components/traffic/LanePanel';
import VideoPanel      from './components/video/VideoPanel';
import HistoryChart    from './components/charts/HistoryChart';
import PredictionPanel from './components/metrics/PredictionPanel';

const API = 'http://localhost:8000';

export default function App() {
  const [aggregation, setAggregation] = useState(null);
  const [rawData,     setRawData]     = useState([]);
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
      const r = await fetch(`${API}/raw-data?limit=5000`);
      if (r.ok) {
        const d = await r.json();
        setRawData(Array.isArray(d?.items) ? d.items : []);
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
    fetchPrediction();

    const t1 = setInterval(fetchAggregation, 5000);
    const t2 = setInterval(fetchRaw,         15000);
    const t3 = setInterval(fetchPrediction,  30000);

    return () => [t1, t2, t3].forEach(clearInterval);
  }, [fetchAggregation, fetchRaw, fetchPrediction]);

  // ─── Video-time sync logic ───────────────────────────────────────
  const sortedRaw = useMemo(() =>
    [...rawData].sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    ),
    [rawData]
  );

  // t=0 video = timestamp nhỏ nhất trong rawData
  const videoStartMs = useMemo(() =>
    sortedRaw.length > 0 ? new Date(sortedRaw[0].timestamp).getTime() : null,
    [sortedRaw]
  );

  // filteredRaw: xe detect trong khoảng [videoStartMs, videoStartMs + videoTime*1000)
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
      <Header />

      <div className="main-grid">
        <div className="area-total">
          <TotalCard rawData={filteredRaw} aggregation={aggregation} />
        </div>

        <div className="area-vehicle-types">
          <VehicleTypes rawData={filteredRaw} />
        </div>

        <div className="area-lanes">
          <LanePanel rawData={filteredRaw} aggregation={aggregation} />
        </div>

        <div className="area-video">
          <VideoPanel onTimeUpdate={setVideoTime} />
        </div>

        <div className="area-predict">
          <PredictionPanel data={prediction} />
        </div>

        {/* Biểu đồ lịch sử — tính từ rawData, không dùng /aggregation/history */}
        <div className="area-chart">
          <HistoryChart
            sortedRaw={sortedRaw}
            videoStartMs={videoStartMs}
            videoTime={videoTime}
          />
        </div>
      </div>
    </div>
  );
}