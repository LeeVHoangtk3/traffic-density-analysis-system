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

export default function TrafficChart({
  chart,
}) {

  return (

    <div>

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
  );
}