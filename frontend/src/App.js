import React, {
  useState,
  useEffect,
  useRef,
} from "react";

import "./App.css";

import { Line } from "react-chartjs-2";

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler
);

const API = "http://localhost:8000";

export default function App() {

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

  // ---> THÊM STATE ĐỂ LƯU KẾT QUẢ TỪ BACKEND / ML SERVICE
  const [apiData, setApiData] = useState({
    congestionLevel: "Loading...",
    prediction: "Loading...",
  });

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

        // SORT TĂNG DẦN
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

  // ĐỒNG BỘ VỚI VIDEO
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

      // FILTER DATA
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

      // THỐNG KÊ XE
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

      // CHART
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

    // VIDEO UPDATE
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


  // ---> THÊM VÒNG LẶP GỌI API ĐỊNH KỲ (5 GIÂY/LẦN) ĐỂ LẤY DỮ LIỆU ML
  useEffect(() => {
    const fetchApiData = async () => {
      try {
        // Lấy mức độ ùn tắc thực tế (Aggregation)
        const aggRes = await fetch(`${API}/aggregation`);
        let congestionLevel = "Unknown";
        if (aggRes.ok) {
           const aggData = await aggRes.json();
           congestionLevel = aggData.congestion_level || "Unknown";
        }

        // Lấy kết quả dự báo từ ML Service (Predict)
        const predRes = await fetch(`${API}/predict-next`);
        let prediction = "Waiting Data...";
        if (predRes.status === 200) {
           const predData = await predRes.json();
           if (predData.predicted_congestion_level) {
              prediction = predData.predicted_congestion_level;
              // Thêm icon minh họa để giống giao diện cũ
              if (prediction === "High" || prediction === "Severe") prediction += " 📈";
              else if (prediction === "Low") prediction += " 📉";
              else prediction += " ➖";
           }
        } else if (predRes.status === 422) {
           prediction = "Not Enough Data";
        }

        // Cập nhật State cho UI
        setApiData({
          congestionLevel,
          prediction
        });

      } catch (err) {
        console.log("Lỗi lấy dữ liệu API:", err);
      }
    };

    fetchApiData(); // Chạy luôn lần đầu tiên
    const interval = setInterval(fetchApiData, 5000); // Thiết lập chu kỳ lặp lại
    return () => clearInterval(interval);
  }, []);
  // ---> KẾT THÚC ĐOẠN THÊM MỚI


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

            <div className="yellow-dot"></div>

            <div>

              <div className="stat-label">
                Congestion Level:
              </div>

              <div className="stat-value">
                {/* HIỂN THỊ BIẾN ĐỘNG THAY VÌ FIX CỨNG "Medium" */}
                {apiData.congestionLevel}
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

          <div className="stat-card">

            <div className="chart-icon">
              📈
            </div>

            <div>

              <div className="stat-label">
                Traffic Prediction:
              </div>

              <div className="stat-value">
                {/* HIỂN THỊ BIẾN ĐỘNG TỪ AI THAY VÌ FIX CỨNG */}
                {apiData.prediction}
              </div>

            </div>

          </div>

        </div>

        <div className="section-title">
          LIVE TRAFFIC FEED
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

        <div className="section-title chart-title">
          TRAFFIC VOLUME TREND
          (24H)
        </div>

        <div className="chart-container">

          <Line
            data={{
              labels:
                chart.labels,

              datasets: [
                {
                  label:
                    "Traffic",

                  data:
                    chart.historicalData,

                  borderColor:
                    "#60a5fa",

                  backgroundColor:
                    "rgba(96,165,250,0.15)",

                  fill: true,

                  tension: 0.4,

                  pointRadius: 0,
                },
              ],
            }}

            options={{
              responsive: true,

              maintainAspectRatio:
                false,

              plugins: {
                legend: {
                  display: false,
                },
              },

              scales: {

                x: {
                  grid: {
                    display: false,
                  },
                },

                y: {
                  beginAtZero: true,

                  grid: {
                    color: "#eee",
                  },
                },

              },
            }}
          />

        </div>

      </div>

    </div>
  );
}