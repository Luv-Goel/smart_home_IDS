# Smart Home IDS - Edge-AI IoT Intrusion Detection System

A production-grade, lightweight network-centric IoT Intrusion Detection System (IDS) running on Raspberry Pi with Edge AI.

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for frontend)
- Raspberry Pi 4/5 (for edge deployment) or x86_64 for cloud backend

### Local Development

```bash
# Clone the repository
git clone https://github.com/your-org/smart_home_IDS.git
cd smart_home_IDS/ids-monorepo

# Start all services locally (dev mode)
docker compose -f infra/docker/docker-compose.dev.yml up --build

# Access the dashboard
open http://localhost:5173
```

### Raspberry Pi Edge Deployment

```bash
# On your Raspberry Pi
docker compose -f infra/docker/docker-compose.edge.yml up -d
```

## 🏗️ Architecture Overview

This monorepo contains:

```
ids-monorepo/
├── apps/                       # Deployable services
│   ├── backend/               # Cloud backend (FastAPI)
│   ├── frontend/              # React dashboard
│   └── edge/                  # Edge services (Raspberry Pi)
├── packages/                  # Shared SDKs
│   ├── ids-core/             # Core utilities
│   ├── ids-schemas/          # Pydantic schemas
│   ├── ids-mqtt/             # MQTT client wrapper
│   ├── ids-models/           # Database models
│   └── ids-ml-plugins/       # ML interface
├── infra/                     # Infrastructure
│   ├── docker/               # Docker configs
│   ├── grafana/              # Monitoring dashboards
│   └── mosquitto/            # MQTT broker config
├── tests/                     # Test suite
├── scripts/                   # Utility scripts
└── docs/                      # Documentation
```

### System Flow

1. **Edge Node (Raspberry Pi)**
   - Packet capture service captures network traffic
   - Feature extraction converts packets to ML features
   - ML inference service runs detection models
   - Fusion engine correlates alerts
   - MQTT service publishes alerts

2. **Cloud Backend**
   - Dashboard API serves REST endpoints
   - WebSocket gateway streams real-time alerts
   - PostgreSQL stores historical data
   - Redis handles pub/sub

## 📦 Services

### Edge Services (Raspberry Pi)

| Service | Description | Port |
|---------|-------------|------|
| packet-capture-service | Raw packet ingestion | - |
| feature-extraction-service | Feature vector extraction | - |
| ml-inference-service | ML model inference | - |
| device-monitor-service | Device tracking & ARP spoofing | - |
| fusion-engine-service | Alert correlation & fusion | - |
| mqtt-alert-service | MQTT publisher | - |

### Cloud Backend Services

| Service | Description | Port |
|---------|-------------|------|
| dashboard-api | REST API endpoints | 8000 |
| websocket-gateway | Real-time alert streaming | 8001 |
| auth-service | JWT authentication | 8002 |
| logging-metrics | Observability endpoints | 9090 |

## 🛠️ Tech Stack

### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy 2.x + Alembic
- Pydantic v2
- AsyncIO
- Redis
- MQTT (paho-mqtt)
- WebSocket

### Edge
- Python 3.11+
- Scapy (packet capture)
- ONNX Runtime
- PyTorch (lightweight)
- scikit-learn

### Frontend
- React 18
- TypeScript
- Vite
- TailwindCSS
- Zustand
- Recharts
- RxJS (for WebSocket)

### Infrastructure
- Docker + Docker Compose
- ARM64 compatible builds
- Grafana + Prometheus
- Mosquitto MQTT Broker

## 🚀 Getting Started

### For Backend Developers

See [Backend Development Guide](docs/backend/development.md)

### For Frontend Developers

See [Frontend Development Guide](docs/frontend/development.md)

### For Edge Developers

See [Edge Deployment Guide](docs/edge/deployment.md)

### For DevOps

See [DevOps Guide](docs/devops/deployment.md)

## 📊 Project Status

- [x] Monorepo structure
- [x] Shared SDK foundations
- [x] FastAPI backend
- [x] Database models
- [x] Docker infrastructure
- [x] React frontend
- [x] Configuration system
- [ ] Edge services implementation
- [ ] ML inference engine
- [ ] Production CI/CD

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'feat: add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📝 License

MIT License - see LICENSE file for details.

## 👥 Team

This project is being developed by 15 parallel implementation agents as part of an automated development pipeline.

## 🙏 Acknowledgments

- Based on the excellent [CICIDS2017 dataset](https://www.unb.ca/cic/datasets/ids-2017.html)
- Uses [Scapy](https://scapy.net/) for packet capture
- Built with [FastAPI](https://fastapi.tiangolo.com/)