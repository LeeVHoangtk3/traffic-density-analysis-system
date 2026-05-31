# 🎨 Frontend Dashboard - React Application

**Frontend** là giao diện người dùng của hệ thống Traffic Density Analysis. Dùng React để hiển thị dữ liệu giao thông real-time, dự báo lưu lượng, và trạng thái đèn tín hiệu.

---

## 📋 Chức Năng Chính

| Chức năng | Mô tả |
|----------|-------|
| **Real-time Dashboard** | Hiển thị mật độ giao thông từ các camera |
| **Dự Báo Lưu Lượng** | Biểu đồ dự báo 15 phút tiếp theo |
| **Trạng Thái Đèn Tín Hiệu** | Thời gian xanh/đỏ hiện tại và tối ưu |
| **Lịch Sử Dữ Liệu** | Truy vấn dữ liệu theo khoảng thời gian |
| **Giám Sát Hiệu Năng** | Biểu đồ quá trình & chỉ số độ chính xác ML |

---

## 🛠️ Công Nghệ

- **React 18+** - Framework UI
- **React Router** - Định tuyến trang
- **Axios** - HTTP client gọi Backend API
- **Chart.js / Recharts** - Biểu đồ dữ liệu
- **Tailwind CSS** - Styling
- **React Hook Form** - Form validation
- **WebSocket** (optional) - Real-time updates

---

## 🚀 Hướng Dẫn Chạy

### Cài Đặt Dependencies

```bash
cd frontend
npm install
```

### Development Mode

```bash
npm start
```

Truy cập: `http://localhost:3000`

### Build Production

```bash
npm run build
```

Tệp output: `frontend/build/`

### Deploy

```bash
# Với Netlify
npm run build
netlify deploy --prod --dir=build

# Với Vercel
vercel --prod

# Với Docker
docker build -t traffic-dashboard .
docker run -p 3000:3000 traffic-dashboard
```

---

## 📁 Cấu Trúc Thư Mục

```
frontend/
├── public/
│   ├── index.html          # HTML chính
│   ├── manifest.json       # PWA manifest
│   └── favicon.ico
│
├── src/
│   ├── components/         # React components tái sử dụng
│   │   ├── Dashboard.jsx
│   │   ├── CameraCard.jsx
│   │   ├── PredictionChart.jsx
│   │   ├── TrafficLightStatus.jsx
│   │   ├── DataTable.jsx
│   │   └── ...
│   │
│   ├── pages/              # Trang chính
│   │   ├── HomePage.jsx
│   │   ├── DetailPage.jsx
│   │   ├── HistoryPage.jsx
│   │   └── ...
│   │
│   ├── hooks/              # Custom React hooks
│   │   ├── useAPI.js       # Hook gọi Backend API
│   │   ├── useWebSocket.js # Hook WebSocket (optional)
│   │   └── ...
│   │
│   ├── services/           # API service layer
│   │   ├── api.js          # Axios instance & base config
│   │   ├── trafficService.js
│   │   ├── predictionService.js
│   │   └── cameraService.js
│   │
│   ├── utils/              # Utility functions
│   │   ├── formatters.js   # Format time, number
│   │   ├── validators.js
│   │   └── constants.js
│   │
│   ├── styles/             # Global styles
│   │   ├── index.css
│   │   ├── tailwind.config.js
│   │   └── theme.css
│   │
│   ├── App.jsx             # Root component
│   ├── index.jsx           # Entry point
│   └── setupProxy.js       # Proxy cấu hình (dev mode)
│
├── package.json
├── package-lock.json
├── .env                    # Biến môi trường
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## ⚙️ Biến Môi Trường (.env)

```env
# Backend API URL
REACT_APP_API_URL=http://localhost:8000

# Polling interval (ms)
REACT_APP_POLLING_INTERVAL=5000

# WebSocket URL (optional)
REACT_APP_WS_URL=ws://localhost:8000/ws

# Feature flags
REACT_APP_ENABLE_WEBSOCKET=false
REACT_APP_ENABLE_ANALYTICS=true

# App info
REACT_APP_TITLE=Traffic Density Analysis System
REACT_APP_VERSION=1.0.0
```

---

## 🔌 API Integration

### Gọi API từ Frontend

```javascript
// services/trafficService.js
import api from './api';

export const getAggregation = async (cameraId, limit = 10) => {
  const response = await api.get('/aggregation', {
    params: { camera_id: cameraId, limit }
  });
  return response.data;
};

export const getRawData = async (cameraId, direction = null) => {
  const response = await api.get('/raw-data', {
    params: { 
      camera_id: cameraId, 
      direction,
      limit: 100 
    }
  });
  return response.data;
};

export const getPrediction = async (cameraId) => {
  const response = await api.get('/predict-next', {
    params: { camera_id: cameraId }
  });
  return response.data;
};
```

### Sử dụng trong Component

```jsx
import { useEffect, useState } from 'react';
import { getAggregation, getPrediction } from '../services/trafficService';

function Dashboard({ cameraId }) {
  const [aggregation, setAggregation] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const agg = await getAggregation(cameraId);
        const pred = await getPrediction(cameraId);
        setAggregation(agg);
        setPrediction(pred);
      } catch (error) {
        console.error('API Error:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000); // Poll mỗi 5s

    return () => clearInterval(interval);
  }, [cameraId]);

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h1>Traffic Dashboard - {cameraId}</h1>
      {aggregation && (
        <div>
          <h2>Current Traffic Level: {aggregation.congestion_level}</h2>
          <p>Total Vehicles: {aggregation.total_vehicles}</p>
          <ul>
            <li>Left: {aggregation.direction_counts.left}</li>
            <li>Straight: {aggregation.direction_counts.straight}</li>
            <li>Right: {aggregation.direction_counts.right}</li>
          </ul>
        </div>
      )}
      {prediction && (
        <div>
          <h2>Next Period Prediction</h2>
          <p>Straight: {prediction.predictions.straight} vehicles</p>
          <p>Phase 1 Green: {prediction.phase_timing.phase_1_green}s</p>
          <p>Phase 2 Green: {prediction.phase_timing.phase_2_green}s</p>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
```

---

## 🔒 CORS Configuration

Nếu Frontend và Backend trên khác origin, cần set CORS ở Backend:

```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🚢 Docker Deployment

```dockerfile
# Dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=build /app/build ./build
EXPOSE 3000
CMD ["serve", "-s", "build", "-l", "3000"]
```

```bash
docker build -t traffic-dashboard .
docker run -p 3000:3000 \
  -e REACT_APP_API_URL=http://backend:8000 \
  traffic-dashboard
```

---

## 📝 Troubleshooting

| Lỗi | Giải pháp |
|-----|---------|
| `CORS error` | Kiểm tra CORS config ở Backend |
| `API 404 error` | Đảm bảo Backend URL đúng ở `.env` |
| `White screen` | Check browser console, run `npm start` again |
| `Port 3000 already in use` | `lsof -ti:3000 \| xargs kill -9` hoặc dùng port khác |

---

## 📚 Tài Liệu Thêm

- [React Documentation](https://react.dev)
- [Create React App Docs](https://create-react-app.dev)
- [Tailwind CSS](https://tailwindcss.com)
- [Recharts Documentation](https://recharts.org)

**Cập nhật lần cuối:** 2026-05-31
