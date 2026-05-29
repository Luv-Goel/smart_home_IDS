# ML Inference Service

Real-time ML inference service for Smart Home IoT Intrusion Detection System (IDS). This service provides anomaly detection using machine learning models with support for multiple backends (ONNX, scikit-learn) and optimization for edge devices (Raspberry Pi).

## Features

- **Multiple Backend Support**: ONNX Runtime, scikit-learn
- **Plugin Architecture**: Easy to add new model types
- **Real-time Inference**: Low-latency predictions
- **Edge Optimization**: Optimized for ARM64/Raspberry Pi
- **Batch Processing**: Efficient batch inference
- **MQTT Integration**: Real-time event processing
- **REST API**: HTTP/WebSocket endpoints
- **Performance Monitoring**: Comprehensive metrics and tracing
- **Model Management**: Hot-swappable models with caching

## Architecture

The service follows a modular architecture:

```
ML Inference Service
├── Inference Engine (core)
│   ├── Model Registry
│   ├── Plugin System
│   └── Performance Monitor
├── API Server (FastAPI)
│   ├── REST Endpoints
│   ├── WebSocket Support
│   └── Prometheus Metrics
├── MQTT Client
│   ├── Async Message Processing
│   ├── Topic Subscription
│   └── Event Publishing
└── Configuration
    ├── Environment Variables
    ├── YAML Configs
    └── Edge Optimization
```

## Supported Model Types

| Model Type | Backend | Edge Compatible | Notes |
|------------|---------|-----------------|-------|
| Random Forest | ONNX, sklearn | ✅ | Recommended for edge |
| Isolation Forest | sklearn | ✅ | Good for anomaly detection |
| One-Class SVM | sklearn | ⚠️ | Higher memory usage |
| Autoencoder | ONNX, sklearn | ✅ | Good for unlabeled data |
| Neural Network | ONNX | ⚠️ | Requires GPU for best performance |

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (optional)
- MQTT broker (optional, for event processing)

### Installation

#### Using Docker (Recommended)

```bash
# Build the image
docker build -t ml-inference-service:latest .

# Run the service
docker run -p 8002:8002 \
  -v ./models:/var/models \
  -e NODE_ID=edge-node-001 \
  -e MQTT_BROKER_URL=mqtt://localhost:1883 \
  ml-inference-service:latest
```

#### From Source

```bash
# Clone the repository
cd ids-monorepo/services/ml-inference-service

# Install dependencies
pip install -r requirements.txt

# Install local packages
pip install -e ../../packages/ids-core
pip install -e ../../packages/ids-schemas
pip install -e ../../packages/ids-ml-plugins

# Run the service
python -m ml_inference_service.main
```

### Docker Compose (Full Stack)

```yaml
version: '3.8'

services:
  ml-inference-service:
    build: ./services/ml-inference-service
    ports:
      - "8002:8002"
    volumes:
      - ./models:/var/models
      - ./logs:/var/log
    environment:
      - NODE_ID=edge-ml-001
      - MQTT_BROKER_URL=mqtt://mosquitto:1883
      - MODEL_DIR=/var/models
      - OPTIMIZE_FOR_EDGE=true
    depends_on:
      - mosquitto
    networks:
      - ids-network

  mosquitto:
    image: eclipse-mosquitto:latest
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/log:/mosquitto/log
    networks:
      - ids-network

networks:
  ids-network:
    driver: bridge
```

## API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/stats` | GET | Service statistics |
| `/model/info` | GET | Model information |
| `/predict` | POST | Single prediction |
| `/predict/batch` | POST | Batch prediction |
| `/model/load` | POST | Load new model |
| `/metrics` | GET | Prometheus metrics |

### MQTT Topics

| Topic | Direction | Description |
|-------|-----------|-------------|
| `ids/edge/+/features` | Subscribe | Receive features for inference |
| `ids/edge/+/inferences` | Publish | Publish inference results |
| `ids/edge/+/ml/status` | Publish | Service status updates |
| `ids/cloud/command/ml` | Subscribe | Control commands |

### Example Usage

#### Single Prediction

```bash
curl -X POST http://localhost:8002/predict \
  -H "Content-Type: application/json" \
  -d '{
    "features": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    "request_id": "req_123",
    "metadata": {
      "device_id": "device_001",
      "flow_id": "flow_123"
    }
  }'
```

Response:
```json
{
  "request_id": "req_123",
  "is_anomaly": false,
  "anomaly_score": 0.15,
  "confidence": 0.85,
  "inference_time_ms": 12.5,
  "model_id": "random_forest_v1",
  "metadata": {
    "processing_time_ms": 15.2,
    "device_id": "device_001"
  }
}
```

#### Batch Prediction

```bash
curl -X POST http://localhost:8002/predict/batch \
  -H "Content-Type: application/json" \
  -d '{
    "batch": [
      {
        "features": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        "request_id": "batch_001"
      },
      {
        "features": [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1],
        "request_id": "batch_002"
      }
    ],
    "batch_id": "batch_123"
  }'
```

#### MQTT Integration

Publish features to MQTT:
```json
{
  "node_id": "edge-node-001",
  "device_id": "device_001",
  "features": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
  "timestamp": "2023-10-27T10:00:00Z",
  "request_id": "req_123"
}
```

Topic: `ids/edge/edge-node-001/features`

Receive inference results:
Topic: `ids/edge/edge-node-001/inferences`

```json
{
  "event_id": "inf_1234567890",
  "node_id": "edge-node-001",
  "timestamp": "2023-10-27T10:00:01Z",
  "model_id": "random_forest_v1",
  "inference_result": {
    "is_anomaly": false,
    "anomaly_score": 0.15,
    "confidence": 0.85,
    "inference_time_ms": 12.5
  },
  "metadata": {
    "device_id": "device_001",
    "processing_time_ms": 15.2
  }
}
```

## Model Management

### Model Directory Structure

```
/var/models/
├── random_forest.onnx
├── isolation_forest.pkl
├── autoencoder.onnx
└── model_metadata/
    ├── random_forest.json
    └── autoencoder.json
```

### Loading Models

#### Via API
```bash
curl -X POST http://localhost:8002/model/load \
  -H "Content-Type: application/json" \
  -d '{
    "model_path": "/var/models/random_forest.onnx",
    "model_id": "rf_edge_v1"
  }'
```

#### Via MQTT Command
```json
{
  "command": "reload_model",
  "node_id": "edge-ml-001",
  "model_path": "/var/models/random_forest.onnx"
}
```

Topic: `ids/cloud/command/ml`

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NODE_ID` | auto-generated | Node identifier |
| `API_HOST` | 0.0.0.0 | API server host |
| `API_PORT` | 8002 | API server port |
| `MODEL_DIR` | /var/models | Model directory |
| `DEFAULT_MODEL` | random_forest.onnx | Default model file |
| `MQTT_BROKER_URL` | mqtt://localhost:1883 | MQTT broker URL |
| `MQTT_CLIENT_ID` | auto-generated | MQTT client ID |
| `LOG_LEVEL` | INFO | Logging level |
| `OPTIMIZE_FOR_EDGE` | false | Enable edge optimizations |
| `INFERENCE_BACKEND` | auto | Backend (onnx, sklearn, auto) |
| `BATCH_SIZE` | 32 | Inference batch size |
| `MAX_QUEUE_SIZE` | 1000 | Request queue size |
| `INFERENCE_THREADS` | 2 | Number of inference threads |
| `HEALTH_CHECK_INTERVAL` | 30 | Health check interval in seconds |

### Edge Optimization

When `OPTIMIZE_FOR_EDGE=true`, the service applies Raspberry Pi optimizations:

- Reduced batch size (16 instead of 32)
- Single inference thread
- Disabled sklearn caching
- Disk-based model cache
- Reduced queue size
- Memory usage limits

## Performance

### Expected Performance

| Metric | Laptop | Raspberry Pi 4 | Notes |
|--------|---------|----------------|-------|
| Inference Time | 5-20ms | 20-100ms | Per sample |
| Throughput | 200-500 req/s | 50-100 req/s | Batch size 32 |
| Memory Usage | 200-500MB | 100-300MB | With model loaded |
| CPU Usage | 10-30% | 30-70% | During inference |

### Monitoring

The service provides comprehensive metrics:

```bash
# Get statistics
curl http://localhost:8002/stats

# Get Prometheus metrics
curl http://localhost:8002/metrics

# Health check
curl http://localhost:8002/health
```

## Development

### Project Structure

```
src/ml_inference_service/
├── __init__.py
├── main.py              # Entry point
├── config.py            # Configuration
├── inference_engine.py  # Core inference engine
├── api_server.py        # FastAPI server
├── mqtt_client.py       # MQTT integration
├── utils.py             # Utilities
└── tests/               # Test suite
```

### Adding New Model Types

1. Create a new detector in `ids-ml-plugins` package
2. Implement the `BaseAnomalyDetector` interface
3. Add factory function to create the detector
4. Register with the model registry

Example:
```python
from ids_ml_plugins import BaseAnomalyDetector, ModelMetadata

class NewDetector(BaseAnomalyDetector):
    def __init__(self, metadata: ModelMetadata):
        super().__init__(metadata)
    
    def load_model(self, model_path: str) -> bool:
        # Load model implementation
        pass
    
    def predict(self, features: np.ndarray) -> InferenceResult:
        # Prediction implementation
        pass
```

### Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=ml_inference_service tests/

# Run specific test
pytest tests/test_inference_engine.py -v

# Run all tests with verbose output
pytest tests/ -v
```

## Deployment

### Kubernetes (Production)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-inference-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ml-inference-service
  template:
    metadata:
      labels:
        app: ml-inference-service
    spec:
      containers:
      - name: ml-inference
        image: ml-inference-service:latest
        ports:
        - containerPort: 8002
        env:
        - name: NODE_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: OPTIMIZE_FOR_EDGE
          value: "false"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1"
        volumeMounts:
        - name: models
          mountPath: /var/models
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: models-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: ml-inference-service
spec:
  selector:
    app: ml-inference-service
  ports:
  - port: 8002
    targetPort: 8002
  type: ClusterIP
```

### Raspberry Pi Deployment

```bash
# Build ARM64 image
docker build --target arm64-runtime -t ml-inference-service:arm64 .

# Run on Raspberry Pi
docker run -d \
  --name ml-inference \
  --restart unless-stopped \
  -p 8002:8002 \
  -v /home/pi/models:/var/models \
  -v /home/pi/logs:/var/log \
  -e NODE_ID=pi-$(hostname) \
  -e OPTIMIZE_FOR_EDGE=true \
  -e MAX_MEMORY_MB=512 \
  ml-inference-service:arm64
```

## Troubleshooting

### Common Issues

1. **Model loading fails**
   - Check model file exists and has correct permissions
   - Verify model format (ONNX vs sklearn)
   - Check feature count matches model expectations

2. **MQTT connection fails**
   - Verify broker URL and port
   - Check network connectivity
   - Verify credentials if using authentication

3. **High memory usage**
   - Enable edge optimization
   - Reduce batch size
   - Monitor with `/stats` endpoint

4. **Slow inference**
   - Check CPU usage
   - Consider model optimization (quantization)
   - Enable batch prediction

### Logs

The service uses structured JSON logging. View logs with:

```bash
# Docker logs
docker logs ml-inference-service

# Follow logs
docker logs -f ml-inference-service

# With jq for pretty JSON
docker logs ml-inference-service | jq .

# Filter by log level
docker logs ml-inference-service 2>&1 | grep -E '"level":"(ERROR|WARNING)"' | jq .
```

## License

MIT License - See [LICENSE](../../LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

- Issues: [GitHub Issues](../../issues)
- Documentation: [Project Wiki](../../wiki)
- Email: security@smarthome.ids