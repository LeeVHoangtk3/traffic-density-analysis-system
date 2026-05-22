import {
  useState,
  useEffect,
  useRef,
} from "react";

import TrafficChart from "./TrafficChart";

const API = "http://localhost:8000";

export default function VideoPlayer() {

  const [stats, setStats] = useState({
    total: 0,
    car: 0,
    motorcycle: 0,
    truck: 0,
    bus: 0,
  });

  const [chart, setChart] = useState({
    labels: [],
    historicalData: [],
  });

  const [allData, setAllData] =
    useState([]);

  const videoRef = useRef(null);

  // FETCH 1 LẦN
  useEffect(() => {

    const fetchData = async () => {

      try {

        const res = await fetch(
          `${API}/raw-data?limit=5000&offset=0`
        );

        const result = await res.json();

        const data =
          result.items || [];

        data.sort(
          (a, b) =>
            new Date(a.timestamp) -
            new Date(b.timestamp)
        );

        setAllData(data);

      } catch (err) {

        console.log(err);

      }
    };

    fetchData();

  }, []);

  // ĐỒNG BỘ VIDEO
  useEffect(() => {

    if (!allData.length) return;

    const video =
      videoRef.current;

    if (!video) return;

    const updateDashboard = () => {

      const currentTime =
        video.currentTime;

      const startTime =
        new Date(
          allData[0].timestamp
        );

      const visibleData =
        allData.filter((e) => {

          const diffSeconds =
            (
              new Date(e.timestamp) -
              startTime
            ) / 1000;

          return (
            diffSeconds <=
            currentTime
          );
        });

      console.log({
        currentTime,
        visible: visibleData.length,
      });

      let counts = {
        car: 0,
        motorcycle: 0,
        truck: 0,
        bus: 0,
      };

      visibleData.forEach((e) => {

        const t =
          e.vehicle_type.toLowerCase();

        if (
          counts[t] !== undefined
        ) {

          counts[t]++;
        }
      });

      setStats({
        total:
          visibleData.length,
        ...counts,
      });

      const time = {};

      visibleData.forEach((e) => {

        const d = new Date(
          e.timestamp
        );

        const key =
          d
            .getHours()
            .toString()
            .padStart(2, "0") +
          ":" +
          d
            .getMinutes()
            .toString()
            .padStart(2, "0");

        time[key] =
          (time[key] || 0) + 1;
      });

      const labels =
        Object.keys(time)
          .sort()
          .slice(-20);

      setChart({
        labels,
        historicalData:
          labels.map(
            (k) => time[k]
          ),
      });
    };

    video.addEventListener(
      "timeupdate",
      updateDashboard
    );

    return () => {

      video.removeEventListener(
        "timeupdate",
        updateDashboard
      );

    };

  }, [allData]);

  return (

    <div>

      <div className="stats-grid">

        <div className="stat-card">

          <div className="stat-icon">
            🚘
          </div>

          <div>

            <div className="stat-label">
              Total Vehicles:
            </div>

            <div className="stat-value">
              {stats.total}
            </div>

          </div>

        </div>

        <div className="stat-card">

          <div>

            <div className="stat-label">
              Vehicle Classification
            </div>

            <div className="vehicle-row">

              <span>
                🚗 {stats.car}
              </span>

              <span>
                🏍️ {stats.motorcycle}
              </span>

              <span>
                🚚 {
                  stats.truck +
                  stats.bus
                }
              </span>

            </div>

          </div>

        </div>

      </div>

      <div className="video-wrapper">

        <video
          ref={videoRef}
          src="http://localhost:8000/video"
          autoPlay
          muted
          controls
        />

      </div>

      <TrafficChart
        chart={chart}
      />

    </div>
  );
}