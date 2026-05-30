import React, { useEffect, useState, useCallback, useMemo } from 'react';
import './App.css';

import Header          from './components/layout/Header';
import TotalCard       from './components/metrics/TotalCard';
import LanePanel       from './components/traffic/LanePanel';
import VideoPanel      from './components/video/VideoPanel';
import HistoryChart    from './components/charts/HistoryChart';
import PredictionPanel from './components/metrics/PredictionPanel';

const API = 'http://localhost:8000';

export default function App() {
  const [aggregation, setAggregation] = useState(null);
  const [rawData,     setRawData]     = useState([]);
  const [prediction,  setPrediction]  = useState(null);
  const [averageStats, setAverageStats] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [videoTime,   setVideoTime]   = useState(0); // giây từ đầu video
  const [videoDuration, setVideoDuration] = useState(0); // độ dài video thực tế
  const [activeCamera, setActiveCamera] = useState('cam01');

  // ─── fetch helpers ───────────────────────────────────────────────
  const fetchAggregation = useCallback(async () => {
    try {
      const r = await fetch(`${API}/aggregation?camera_id=${activeCamera}`);
      if (r.ok) setAggregation(await r.json());
    } catch {}
  }, [activeCamera]);

  const fetchRaw = useCallback(async () => {
    try {
      const r = await fetch(`${API}/raw-data?camera_id=${activeCamera}&limit=5000`);
      if (r.ok) {
        const d = await r.json();
        setRawData(Array.isArray(d?.items) ? d.items : []);
      }
    } catch {}
  }, [activeCamera]);

  const fetchPrediction = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/predict-next?camera_id=${activeCamera}`);
      if (r.ok) setPrediction(await r.json());
    } catch {}
  }, [activeCamera]);

  const fetchAverage = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/traffic/average?camera_id=${activeCamera}`);
      if (r.ok) setAverageStats(await r.json());
    } catch {}
  }, [activeCamera]);

  const fetchHistory = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/traffic/history?camera_id=${activeCamera}`);
      if (r.ok) {
        const d = await r.json();
        setHistoryData(Array.isArray(d?.items) ? d.items : []);
      }
    } catch {}
  }, [activeCamera]);

  // ─── initial load + polling ──────────────────────────────────────
  useEffect(() => {
    fetchAggregation();
    fetchRaw();
    fetchPrediction();
    fetchAverage();
    fetchHistory();

    const t1 = setInterval(fetchAggregation, 5000);
    const t2 = setInterval(fetchRaw,         15000);
    const t3 = setInterval(fetchPrediction,  30000);
    const t4 = setInterval(fetchAverage,     30000);
    const t5 = setInterval(fetchHistory,     15000);

    return () => [t1, t2, t3, t4, t5].forEach(clearInterval);
  }, [fetchAggregation, fetchRaw, fetchPrediction, fetchAverage, fetchHistory]);

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

  const videoEndMs = useMemo(() =>
    sortedRaw.length > 0 ? new Date(sortedRaw[sortedRaw.length - 1].timestamp).getTime() : null,
    [sortedRaw]
  );

  const virtualDurationMs = useMemo(() => {
    if (videoStartMs && videoEndMs) {
      return videoEndMs - videoStartMs;
    }
    return 0;
  }, [videoStartMs, videoEndMs]);

  // filteredRaw: xe detect trong khoảng [videoStartMs, videoStartMs + videoTime * scale * 1000)
  const filteredRaw = useMemo(() => {
    if (!videoStartMs || !sortedRaw.length) return [];
    
    // Tính hệ số co giãn tỉ lệ K: virtual_duration / physical_duration
    let scale = 1.0;
    if (videoDuration > 0 && virtualDurationMs > 0) {
      scale = (virtualDurationMs / 1000) / videoDuration;
    }
    
    const cutoffMs = videoStartMs + videoTime * scale * 1000;
    return sortedRaw.filter(d => {
      const ts = new Date(d.timestamp).getTime();
      return ts >= videoStartMs && ts < cutoffMs;
    });
  }, [sortedRaw, videoStartMs, virtualDurationMs, videoTime, videoDuration]);

  const handleTimeUpdate = useCallback((time, duration) => {
    setVideoTime(time);
    if (duration) setVideoDuration(duration);
  }, []);

  const handleCameraChange = useCallback((newCam) => {
    setActiveCamera(newCam);
    // Reset video time to 0 to restart video playback
    setVideoTime(0);
    setVideoDuration(0);
  }, []);

  return (
    <div className="app">
      <Header activeCamera={activeCamera} onChangeCamera={handleCameraChange} />

      <div className="main-grid">
        <div className="area-total">
          <TotalCard rawData={filteredRaw} aggregation={aggregation} averageStats={averageStats} />
        </div>

        <div className="area-lanes">
          <LanePanel rawData={filteredRaw} aggregation={aggregation} />
        </div>

        <div className="area-video">
          <VideoPanel onTimeUpdate={handleTimeUpdate} activeCamera={activeCamera} />
        </div>

        <div className="area-predict">
          <PredictionPanel data={prediction} />
        </div>

        {/* Biểu đồ lịch sử — sử dụng dữ liệu thực tế từ database history */}
        <div className="area-chart">
          <HistoryChart
            historyData={historyData}
            videoStartMs={videoStartMs}
            videoTime={videoTime}
            videoDuration={videoDuration}
          />
        </div>
      </div>
    </div>
  );
}