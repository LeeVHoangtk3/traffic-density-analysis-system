import "./App.css";
import Header           from "./components/Header";
import StatsBar         from "./components/StatsBar";
import TrafficLightPanel from "./components/TrafficLightPanel";
import LaneStatusGrid   from "./components/LaneStatusGrid";
import ForecastChart    from "./components/ForecastChart";
import VideoPlayer      from "./components/VideoPlayer";

export default function App() {
  return (
    <div className="app">
      <div className="dashboard">

        <Header />
        <StatsBar />

        <div className="row-2">
          <TrafficLightPanel />
          <LaneStatusGrid />
        </div>

        <ForecastChart />
        <VideoPlayer />

      </div>
    </div>
  );
}