# Smart Home IDS - Complete Production Implementation

## 🚀 Overview

This is a complete production-grade IoT Intrusion Detection System (IDS) for smart homes using Edge AI on Raspberry Pi. The system implements the complete pipeline from research paper architecture:

**Packet Capture → Feature Extraction → Device Monitoring → ML Inference → Fusion Engine → Threshold Evaluation → MQTT Event Bus → Dashboard + Alerts**

## 🏗️ System Architecture

### Complete Monorepo Structure

```
ids-monorepo/
├── apps/
│   ├── frontend/          # React/TypeScript dashboard
│   ├── backend/           # FastAPI backend services
│   └── edge/              # Raspberry Pi edge services
├── packages/              # Shared internal libraries
│   ├── ids-core/          # Core utilities and config
│   ├── ids-schemas/       # Pydantic schemas
│   ├── ids-models/        # SQLAlchemy models
│   ├── ids-mqtt/          # MQTT client wrappers
│   └── ids-ml-plugins/    # ML plugin framework
├── services/              # Production services
│   ├── packet-capture-service/     # Real-time packet capture
│   ├── feature-extraction-service/ # Feature extraction
│   ├── ml-inference-service/       # ML inference
│   └── fusion-engine-service/      # Cost-aware fusion
├── infra/                 # Infrastructure
│   ├── docker/           # Docker configurations
│   ├── mosquitto/        # MQTT broker configs
│   └── grafana/          # Monitoring dashboards
├── scripts/              # Deployment scripts
├── tests/                # Comprehensive test suite
└── docs/                 # Documentation
```

## 🔧 Core Implementation Status

### ✅ COMPLETED
1. **Shared SDK Packages**
   - `ids-core`: Configuration management, logging, async API client
   - `ids-ml-plugins`: Plugin-based ML framework with ONNX/scikit-learn support
   - Enhanced structured logging with performance metrics

2. **ML Inference Service** (FULLY IMPLEMENTED)
   - ONNX Runtime integration for edge devices
   - scikit-learn model support
   - Batch inference with performance optimization
   - Async FastAPI server with health checks
   - MQTT integration for event-driven processing
   - ARM64/Raspberry Pi optimized Dockerfiles

3. **Fusion Engine Service** (CORE IMPLEMENTED)
   - **Research paper fusion equation**: 
     `\hat{p}_t = σ(β₀ + β₁s_t^{dev} + β₂s_t^{flow} + β₃s_t^{dev}s_t^{flow})`
   - **Cost-aware threshold optimization**:
     `J(τ) = C_FN * P_FN(τ) + C_FP * P_FP(τ)`
   - Multiple fusion strategies and confidence methods
   - Adaptive threshold learning
   - Complete FastAPI server

### ⚠️ PARTIALLY COMPLETED
1. **Packet Capture Service** - Basic implementation exists
2. **Feature Extraction Service** - Structure exists
3. **Device Monitoring Service** - Needs implementation
4. **WebSocket Gateway** - Needs implementation
5. **Frontend Dashboard** - Needs implementation
6. **Authentication System** - Needs implementation

## 🧪 Key Features Implemented

### ML Inference Engine
- **Multiple backend support**: ONNX Runtime, scikit-learn
- **Plugin architecture**: Easy to add new model types
- **Edge optimization**: ARM64 and Raspberry Pi specific optimizations
- **Performance tracking**: Inference time, memory usage, batch processing
- **Robust error handling**: Graceful degradation and retry logic

### Fusion Engine
- **Linear fusion**: Implements research paper equation exactly
- **Cost-aware threshold optimization**: Minimizes total cost of errors
- **Adaptive learning**: Updates thresholds based on historical data
- **Multiple severity levels**: Low, Medium, High, Critical
- **Confidence adjustment**: Lower confidence → higher threshold

### Production Features
- **Structured logging**: JSON logs with distributed tracing
- **Health checks**: Docker health checks and API endpoints
- **Performance metrics**: Prometheus metrics collection
- **Async architecture**: Non-blocking I/O throughout
- **Docker ready**: Multi-stage builds for production

## 🐳 Docker Deployment

### Quick Start
```bash
# Clone the repository
git clone https://github.com/Luv-Goel/smart_home_IDS.git
cd smart_home_IDS/ids-monorepo

# Start all services
docker-compose -f infra/docker/docker-compose.cloud.yml up -d
```

### Edge Deployment (Raspberry Pi)
```bash
# Build ARM64 optimized images
docker buildx build --platform linux/arm64 -t ids-service:arm64 .

# Run edge services
docker-compose -f infra/docker/docker-compose.edge.yml up -d
```

## 📊 API Endpoints

### ML Inference Service (`localhost:8002`)
- `GET /health` - Health check
- `GET /stats` - Engine statistics
- `POST /predict` - Single prediction
- `POST /predict/batch` - Batch prediction
- `GET /model/info` - Model information

### Fusion Engine Service (`localhost:8003`)
- `GET /health` - Health check
- `GET /stats` - Engine statistics
- `POST /fuse` - Fuse anomaly scores
- `GET /threshold` - Current threshold
- `POST /threshold/optimize` - Trigger optimization
- `GET /config` - Current configuration

## 🔬 Research Implementation

### Fusion Equation
```
\hat{p}_t = σ(β₀ + β₁s_t^{dev} + β₂s_t^{flow} + β₃s_t^{dev}s_t^{flow})
```

Where:
- `σ(x)` = Sigmoid activation function
- `β₀`, `β₁`, `β₂`, `β₃` = Learned coefficients
- `s_t^{dev}` = Device anomaly score
- `s_t^{flow}` = Flow anomaly score

### Cost Function
```
J(τ) = C_FN * P_FN(τ) + C_FP * P_FP(τ)
```

Where:
- `C_FN` = Cost of false negative (missing attack)
- `C_FP` = Cost of false positive (false alarm)
- `P_FN(τ)` = False negative rate at threshold τ
- `P_FP(τ)` = False positive rate at threshold τ

## 🚧 Next Implementation Steps

1. **Complete frontend dashboard** with real-time WebSocket updates
2. **Implement device monitoring engine** with rogue device detection
3. **Add authentication system** with JWT and RBAC
4. **Create demo pipeline** with synthetic attack simulations
5. **Add comprehensive testing** with unit and integration tests
6. **Implement CI/CD pipeline** with GitHub Actions
7. **Create deployment scripts** for Raspberry Pi

## 📋 Requirements

- Python 3.11+
- Docker & Docker Compose
- Redis (for caching)
- Mosquitto MQTT broker
- PostgreSQL (optional, SQLite for edge)
- ONNX Runtime (for ML inference)

## 📄 License

MIT License - See LICENSE file for details

## 👨‍💻 Author

Security Research Team - Edge AI IoT Security Project