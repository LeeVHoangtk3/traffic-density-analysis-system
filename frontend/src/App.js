import React, { useEffect, useState, useCallback, useMemo } from 'react';
import './App.css';

import Header          from './components/layout/Header';
import VideoPanel      from './components/video/VideoPanel';
import HistoryChart    from './components/charts/HistoryChart';
import PredictionPanel from './components/metrics/PredictionPanel';

const API = 'http://127.0.0.1:8000';

export default function App() {
  const [rawData,     setRawData]     = useState([]);
  const [prediction,  setPrediction]  = useState(null);
  const [averageStats, setAverageStats] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [videoTime,   setVideoTime]   = useState(0); // giây từ đầu video
  const [videoDuration, setVideoDuration] = useState(0); // độ dài video thực tế
  const [activeCamera, setActiveCamera] = useState('cam01');
  const [outputVideos, setOutputVideos] = useState([]);
  const [activeVideo, setActiveVideo] = useState('cam01-traffic3_output.mp4');

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
    fetchRaw();
    fetchPrediction();
    fetchAverage();
    fetchHistory();

    const t2 = setInterval(fetchRaw,         15000);
    const t3 = setInterval(fetchPrediction,  30000);
    const t4 = setInterval(fetchAverage,     30000);
    const t5 = setInterval(fetchHistory,     15000);

    return () => [t2, t3, t4, t5].forEach(clearInterval);
  }, [fetchRaw, fetchPrediction, fetchAverage, fetchHistory]);

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



  // ─── fetch output videos list on mount ────────────────────────────
  useEffect(() => {
    async function fetchVideos() {
      try {
        const r = await fetch(`${API}/videos/outputs`);
        if (r.ok) {
          const vids = await r.json();
          setOutputVideos(vids);
          if (vids.length > 0) {
            let matched = null;
            if (activeCamera === 'cam01') {
              matched = vids.find(v => v === 'cam01-traffic3_output.mp4');
            } else if (activeCamera === 'cam02') {
              matched = vids.find(v => v === 'cam02-traffic5_output.mp4');
            }
            if (!matched) {
              matched = vids.find(v => v.startsWith(activeCamera));
            }
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
      let matched = null;
      if (newCam === 'cam01') {
        matched = outputVideos.find(v => v === 'cam01-traffic3_output.mp4');
      } else if (newCam === 'cam02') {
        matched = outputVideos.find(v => v === 'cam02-traffic5_output.mp4');
      }
      if (!matched) {
        matched = outputVideos.find(v => v.startsWith(newCam));
      }
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

  // Cập nhật currentMs đồng bộ với thước đo biểu đồ lịch sử
  const currentMs = useMemo(() => {
    if (!videoStartMs) return null;
    let scale = 1.0;
    if (videoDuration > 0 && virtualDurationMs > 0) {
      scale = (virtualDurationMs / 1000) / videoDuration;
    }
    return videoStartMs + videoTime * scale * 1000;
  }, [videoStartMs, videoTime, videoDuration, virtualDurationMs]);

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
            currentMs={currentMs}
            averageStats={averageStats}
          />
        </div>

      </div>
    </div>
  );
}