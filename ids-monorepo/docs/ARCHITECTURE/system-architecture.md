# System Architecture

This document describes the architecture of Smart Home IDS.

## Overview

Smart Home IDS is a distributed system designed for real-time IoT network monitoring with edge AI capabilities. The architecture follows a hub-and-spoke model with edge nodes collecting and processing network traffic, and a central backend for storage, analysis, and visualization.

## Architecture Layers

### Edge Layer

The edge layer runs on Raspberry Pi devices and handles:

- **Packet Capture**: Real-time network traffic capture using Scapy
- **Feature Extraction**: Conversion of raw packets to ML features
- **ML Inference**: Lightweight anomaly detection using ONNX models
- **Device Monitoring**: Tracking of IoT device presence and behavior
- **Alert Correlation**: Fusion of multiple detection signals

### Cloud Layer

The cloud layer provides:

- **REST API**: Backend services for data access
- **WebSockets**: Real-time alert streaming
- **Database**: Historical data storage in PostgreSQL
- **Frontend**: React-based dashboard

## Data Flow

```
IoT Network → Packet Capture → Feature Extraction → ML Inference → Alert Fusion → MQTT Publish
                                                                                 ↓
                                                          WebSocket Gateway → Frontend
                                                                                 ↓
                                                          REST API → PostgreSQL
```

## Component Details

### Packet Capture Service

- **Technology**: Scapy, Python
- **Function**: Raw packet capture
- **Output**: Packet information to MQTT
- **Performance**: Optimized for Raspberry Pi

### Feature Extraction Service

- **Technology**: Python, NumPy
- **Function**: Extract flow features from packets
- **Output**: Feature vectors to MQTT
- **Features**: Duration, packet count, byte rates, etc.

### ML Inference Service

- **Technology**: ONNX Runtime, Scikit-learn
- **Function**: Anomaly detection
- **Models**: Random Forest, Autoencoders
- **Output**: Anomaly scores and categories

### Fusion Engine Service

- **Function**: Correlate multiple detection signals
- **Logic**: Cost-aware thresholding
- **Output**: Confirmed alerts to MQTT

### MQTT Broker

- **Technology**: Eclipse Mosquitto
- **Topics**: Hierarchical topic structure
- **QoS**: Protocol-based reliability

### Backend Services

- **Technology**: FastAPI, SQLAlchemy
- **Functions**:
  - REST API endpoints
  - WebSocket streaming
  - Database operations
  - Alert management

### Frontend

- **Technology**: React, TypeScript, Vite
- **Features**:
  - Real-time alert display
  - Device management
  - Historical data visualization
  - Configuration UI

## Security Architecture

### Encryption
- TLS for all external communication
- MQTT with optional TLS
- Database encryption at rest

### Authentication
- JWT for API authentication
- OAuth2 for user management
- Role-based access control (RBAC)

### Network Security
- Container isolation
- Network policies
- Non-root users

## Scalability Considerations

### Horizontal Scaling
- Frontend: CDN + multiple instances
- Backend: Load balancer + multiple instances
- Edge: Multiple Raspberry Pi nodes

### Vertical Scaling
- Database: Connection pooling
- Edge: Resource limits
- ML: Batch processing optimization

## High Availability

- PostgreSQL: Replication
- Redis: Sentinel
- MQTT: Clustering
- Edge: Redundant deployments

## Monitoring

- Prometheus: Metrics collection
- Grafana: Visualization
- Structured logging: Error tracking
- Health checks: Service monitoring

## Fault Tolerance

- Retry logic for MQTT messages
- Local buffering for edge nodes
- Database transaction recovery
- Graceful degradation