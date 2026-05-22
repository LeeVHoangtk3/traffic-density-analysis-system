import "./App.css";

import StatsGrid from "./components/StatsGrid";
import VideoPlayer from "./components/VideoPlayer";

export default function App() {

  return (

    <div className="app">

      <div className="dashboard">

        <h1 className="title">
          CITY TRAFFIC MONITOR
        </h1>

        <div className="subtitle">
          REALTIME TRAFFIC
          STATISTICS
        </div>

        <StatsGrid />

        <div className="section-title">
          LIVE TRAFFIC FEED
        </div>

        <VideoPlayer />

      </div>

    </div>
  );
}