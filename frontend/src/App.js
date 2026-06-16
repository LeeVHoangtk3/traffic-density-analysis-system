import React, { useEffect, useState, useCallback, useMemo } from 'react';
import './App.css';

import Header          from './components/layout/Header';
import VideoPanel      from './components/video/VideoPanel';
import HistoryChart    from './components/charts/HistoryChart';
import PredictionPanel from './components/metrics/PredictionPanel';

const API = 'http://127.0.0.1:8000';

export default function App() {
  const [aggregation, setAggregation] = useState(null);
  const [rawData,     setRawData]     = useState([]);
  const [prediction,  setPrediction]  = useState(null);
  const [averageStats, setAverageStats] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [videoTime,   setVideoTime]   = useState(0); // giây từ đầu video
  const [videoDuration, setVideoDuration] = useState(0); // độ dài video thực tế
  const [activeCamera, setActiveCamera] = useState('cam01');
  const [outputVideos, setOutputVideos] = useState([]);
  const [activeVideo, setActiveVideo] = useState('cam01-traffic3_output.mp4');

  // ─── fetch helpers: Gộp luồng dữ liệu 3 camera thành 1 hành trình làn đơn ───
  const fetchAggregation = useCallback(async () => {
    try {
      const [r1, r2, r3] = await Promise.all([
        fetch(`${API}/aggregation?camera_id=cam01`),
        fetch(`${API}/aggregation?camera_id=cam02`),
        fetch(`${API}/aggregation?camera_id=cam03`),
      ]);
      let combined = {
        camera_id: "Làn đường đơn",
        vehicle_count: 0,
        inbound_count: 0,
        queue_proxy: 0
      };
      const add = (data) => {
        combined.vehicle_count += data.vehicle_count || 0;
        combined.inbound_count += data.inbound_count || 0;
        combined.queue_proxy += data.queue_proxy || 0;
      };

      if (r1.ok) add(await r1.json());
      if (r2.ok) add(await r2.json());
      if (r3.ok) add(await r3.json());
      
      let level = "Low";
      if (combined.vehicle_count >= 150) level = "Heavy";
      else if (combined.vehicle_count >= 80) level = "High";
      else if (combined.vehicle_count >= 30) level = "Medium";
      combined.congestion_level = level;
      
      setAggregation(combined);
    } catch {}
  }, []);

  const fetchRaw = useCallback(async () => {
    try {
      const [r1, r2, r3] = await Promise.all([
        fetch(`${API}/raw-data?camera_id=cam01&limit=3000`),
        fetch(`${API}/raw-data?camera_id=cam02&limit=3000`),
        fetch(`${API}/raw-data?camera_id=cam03&limit=3000`),
      ]);
      let items = [];
      if (r1.ok) { const d = await r1.json(); if (d.items) items.push(...d.items); }
      if (r2.ok) { const d = await r2.json(); if (d.items) items.push(...d.items); }
      if (r3.ok) { const d = await r3.json(); if (d.items) items.push(...d.items); }
      setRawData(items);
    } catch {}
  }, []);

  const fetchPrediction = useCallback(async () => {
    try {
      // Dự báo theo phân đoạn camera được chọn hiện tại để có độ chính xác cao nhất
      const r = await fetch(`${API}/api/v1/predict-next?camera_id=${activeCamera}`);
      if (r.ok) setPrediction(await r.json());
    } catch {}
  }, [activeCamera]);

  const fetchAverage = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/traffic/average?limit=24`);
      if (r.ok) setAverageStats(await r.json());
    } catch {}
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/traffic/history?limit=24`);
      if (r.ok) {
        const data = await r.json();
        if (data && Array.isArray(data.items)) {
          setHistoryData(data.items);
        }
      }
    } catch {}
  }, []);

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

  // ─── fetch output videos list on mount ────────────────────────────
  useEffect(() => {
    async function fetchVideos() {
      try {
        const r = await fetch(`${API}/videos/outputs`);
        if (r.ok) {
          const vids = await r.json();
          setOutputVideos(vids);
          if (vids.length > 0) {
            const matched = vids.find(v => v.startsWith(activeCamera));
            if (matched) {
              setActiveVideo(matched);
            } else {
              setActiveVideo(vids[0]);
            }
          }
        }
      } catch (err) {
        console.error("Failed to fetch output videos", err);
      }
    }
    fetchVideos();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleTimeUpdate = useCallback((time, duration) => {
    setVideoTime(time);
    if (duration) setVideoDuration(duration);
  }, []);

  const handleCameraChange = useCallback((newCam) => {
    setActiveCamera(newCam);
    setVideoTime(0);
    setVideoDuration(0);
    
    // Auto-select a matching video for this camera
    if (outputVideos.length > 0) {
      const matched = outputVideos.find(v => v.startsWith(newCam));
      if (matched) {
        setActiveVideo(matched);
      }
    }
  }, [outputVideos]);

  const handleVideoChange = useCallback((newVid) => {
    setActiveVideo(newVid);
    setVideoTime(0);
    setVideoDuration(0);
    
    // Auto-detect camera ID from video name
    const match = newVid.match(/^(cam\d+)/i);
    if (match) {
      const detectedCam = match[1].toLowerCase();
      setActiveCamera(detectedCam);
    }
  }, []);

  return (
    <div className="app">
      <Header
        activeCamera={activeCamera}
        onChangeCamera={handleCameraChange}
        activeVideo={activeVideo}
        onChangeVideo={handleVideoChange}
        outputVideos={outputVideos}
      />

      <div className="main-grid">
        <div className="area-video">
          <VideoPanel
            onTimeUpdate={handleTimeUpdate}
            activeCamera={activeCamera}
            activeVideo={activeVideo}
          />
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
            averageStats={averageStats}
          />
        </div>
      </div>
    </div>
  );
}