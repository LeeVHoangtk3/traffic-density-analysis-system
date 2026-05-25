import {
  useState,
  useEffect,
} from "react";

import StatCard from "./StatCard";

const API = "http://localhost:8000";

export default function StatsGrid() {

  const [apiData, setApiData] = useState({
    congestionLevel: "Loading...",
    prediction: "Loading...",
  });

  useEffect(() => {

    const fetchApiData = async () => {

      try {

        const aggRes = await fetch(
          `${API}/aggregation`
        );

        let congestionLevel =
          "Unknown";

        if (aggRes.ok) {

          const aggData =
            await aggRes.json();

          congestionLevel =
            aggData.congestion_level ||
            "Unknown";
        }

        const predRes = await fetch(
          `${API}/predict-next`
        );

        let prediction =
          "Waiting Data...";

        if (predRes.status === 200) {

          const predData =
            await predRes.json();

          if (
            predData.predicted_congestion_level
          ) {

            prediction =
              predData.predicted_congestion_level;

            if (
              prediction === "High" ||
              prediction === "Severe"
            ) {

              prediction += " 📈";

            } else if (
              prediction === "Low"
            ) {

              prediction += " 📉";

            } else {

              prediction += " ➖";

            }
          }

        } else if (
          predRes.status === 422
        ) {

          prediction =
            "Not Enough Data";
        }

        setApiData({
          congestionLevel,
          prediction,
        });

      } catch (err) {

        console.log(
          "Lỗi lấy dữ liệu API:",
          err
        );

      }
    };

    fetchApiData();

    const interval =
      setInterval(
        fetchApiData,
        5000
      );

    return () =>
      clearInterval(interval);

  }, []);

  return (

    <div className="stats-grid">

      <StatCard>

        <div className="yellow-dot"></div>

        <div>

          <div className="stat-label">
            Congestion Level:
          </div>

          <div className="stat-value">
            {apiData.congestionLevel}
          </div>

        </div>

      </StatCard>

      <StatCard>

        <div className="chart-icon">
          📈
        </div>

        <div>

          <div className="stat-label">
            Traffic Prediction:
          </div>

          <div className="stat-value">
            {apiData.prediction}
          </div>

        </div>

      </StatCard>

    </div>
  );
}