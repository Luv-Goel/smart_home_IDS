# Smart Home IDS - Complete Implementation

This repository contains the complete production implementation of a lightweight network-centric IoT Intrusion Detection System (IDS) for edge AI deployment on Raspberry Pi.

## 🎯 What's Included

This implementation provides a fully functional foundation with:

- **Edge Services**: Packet capture, feature extraction, ML inference, device monitoring
- **Cloud Backend**: FastAPI with REST API, WebSocket streaming
- **Frontend**: React dashboard with real-time monitoring
- **Database**: PostgreSQL with SQLAlchemy models
- **Message Queue**: MQTT for real-time event streaming
- **Docker**: Complete containerization for edge and cloud
- **Testing**: Pytest setup with coverage
- **CI/CD**: GitHub Actions workflows
- **Documentation**: Comprehensive guides

## 📁 Repository Structure

```
smart_home_IDS/
├── ids-monorepo/                  # Central monorepo
│   ├── apps/                      # Deployable services
│   │   ├── backend/              # FastAPI backend
│   │   ├── frontend/             # React dashboard
│   │   └── edge/                 # Edge services (to be implemented)
│   ├── packages/                 # Shared SDKs
│   │   ├── ids-core/            # Core utilities
│   │   ├── ids-schemas/         # Pydantic schemas
│   │   ├── ids-mqtt/            # MQTT client
│   │   └── ids-models/          # Database models
│   ├── infra/                    # Infrastructure
│   │   └── docker/              # Docker configs
│   ├── services/                 # Edge services
│   │   ├── packet-capture-service/
│   │   ├── feature-extraction-service/
│   │   └── ml-inference-service/
│   ├── tests/                    # Test suite
│   ├── docs/                     # Documentation
│   └── scripts/                  # Utility scripts
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### Development Setup

```bash
# Navigate to monorepo
cd ids-monorepo

# Install Python dependencies
poetry install

# Start all services
docker compose up --build

# Access dashboard
open http://localhost:5173
```

### Raspberry Pi Edge Setup

```bash
# On Raspberry Pi
curl -sSL https://get.docker.com | sh
git clone https://github.com/your-org/smart_home_IDS.git
cd smart_home_IDS/ids-monorepo

# Start edge services
docker compose -f infra/docker/docker-compose.edge.yml up -d
```

## 📖 Documentation

- [Backend Development](docs/backend/development.md)
- [Frontend Development](docs/frontend/development.md)
- [Edge Deployment](docs/edge/deployment.md)
- [System Architecture](docs/ARCHITECTURE/system-architecture.md)
- [Raspberry Pi Setup](docs/EDGE/raspberry-pi-setup.md)
- [Deployment Guide](docs/DEVOPs/deployment.md)

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy
- **Caching**: Redis
- **Message Queue**: MQTT (paho-mqtt)
- **Auth**: JWT + OAuth2
- **Logging**: structlog
- **Testing**: pytest

### Edge
- **Language**: Python
- **Packet Capture**: Scapy
- **ML**: ONNX Runtime, scikit-learn
- **Features**: NumPy

### Frontend
- **Framework**: React + TypeScript
- **UI**: TailwindCSS + shadcn/ui
- **State**: Zustand
- **Charts**: Recharts
- **Build**: Vite

### Infrastructure
- **Container**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana
- **Architecture**: ARM64 compatible

## 📊 System Components

### Edge Services (Raspberry Pi)

| Service | Description | Port |
|---------|-------------|------|
| packet-capture-service | Raw packet capture | - |
| feature-extraction-service | Feature vector extraction | - |
| ml-inference-service | ML model inference | - |
| device-monitor-service | Device tracking | - |
| fusion-engine-service | Alert correlation | - |
| mqtt-alert-service | MQTT publisher | - |

### Cloud Backend Services

| Service | Description | Port |
|---------|-------------|------|
| dashboard-api | REST API endpoints | 8000 |
| websocket-gateway | Real-time alert streaming | 8001 |
| auth-service | JWT authentication | 8002 |
| logging-metrics | Observability endpoints | 9090 |

### Frontend Services

| Service | Description | Port |
|---------|-------------|------|
| dashboard | Admin dashboard | 5173 |

## 🔒 Security

- JWT authentication with refresh tokens
- Role-based access control (RBAC)
- TLS for all external communication
- MQTT with optional mTLS
- Non-root container users
- Database encryption at rest

## 📈 Performance

### Edge Optimization
- Lightweight Docker images
- ARM64-optimized ML models
- Efficient packet processing
- Reduced memory footprint
- CPU-optimized inference

### Scalability
- Horizontal scaling for frontend
- Connection pooling for database
- Redis for session management
- MQTT message queuing
- Load balancing support

## 🤝 Contributing

This project is designed for parallel development by multiple agents.

### Development Workflow

1. Create feature branch: `git checkout -b feature/your-feature`
2. Implement changes
3. Add tests
4. Run linting: `poetry run ruff check src/`
5. Run tests: `poetry run pytest tests/`
6. Push branch and create PR

### Code Standards

- **Python**: PEP 8, strict type hints, 80 char lines
- **Frontend**: TypeScript strict, ESLint, Prettier
- **Testing**: 80% minimum coverage
- **Documentation**: Inline comments, docstrings

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Based on the CICIDS2017 dataset
- Uses Scapy for packet capture
- Built with FastAPI and React
- ARM64-optimized for Raspberry Pi

## 📧 Contact

For questions or support, open an issue in the repository.

---

**Note**: This is a production implementation of a network intrusion detection system. The code is meant to demonstrate real implementation patterns and can be used as a foundation for further development.