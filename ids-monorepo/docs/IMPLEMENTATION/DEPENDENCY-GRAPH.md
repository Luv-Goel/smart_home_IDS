# Service Dependency Graph

This document describes dependencies between services in Smart Home IDS.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        IoT Network                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │ IoT Device │  │ IoT Device │  │ IoT Device │                │
│  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘                │
│         │               │               │                       │
│         └───────────────┴───────────────┘                       │
│                           │                                     │
│                    ┌──────▼──────┐                              │
│                    │ Network Link│                              │
│                    └──────┬──────┘                              │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Edge Layer                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Raspberry Pi Node                      │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────┐ │   │
│  │  │ Packet Capture │→ │ Feature        │→ │ ML         │ │   │
│  │  │ Service        │  │ Extraction     │  │ Inference  │ │   │
│  │  └────────┬───────┘  └────────┬───────┘  └──────┬─────┘ │   │
│  │           │                  │                  │        │   │
│  │           ▼                  ▼                  ▼        │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────┐ │   │
│  │  │ Device Monitor │  │ Fusion Engine  │  │ MQTT       │ │   │
│  │  │ Service        │  │ Service        │  │ Alert      │ │   │
│  │  └────────────────┘  └────────────────┘  │ Service    │ │   │
│  │                                           └────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│                     ┌─────────────────┐                        │
│                     │ MQTT Broker     │                        │
│                     └─────────────────┘                        │
└────────────────────────────────┼────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Cloud Layer                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Backend Services                       │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────┐ │   │
│  │  │ Dashboard API  │  │ WebSocket      │  │ Auth       │ │   │
│  │  │ Service        │  │ Gateway        │  │ Service    │ │   │
│  │  └────────┬───────┘  └────────┬───────┘  └────────────┘ │   │
│  │           │                  │                           │   │
│  │           ▼                  ▼                           │   │
│  │  ┌────────────────┐  ┌────────────────┐                 │   │
│  │  │ PostgreSQL     │  │ Redis          │                 │   │
│  │  │ Database       │  │ Cache/Queue    │                 │   │
│  │  └────────────────┘  └────────────────┘                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│                     ┌─────────────────┐                        │
│                     └─────────────────┘                        │
│                         Frontend                               │
│                    (React Dashboard)                           │
└─────────────────────────────────────────────────────────────────┘
```

## Service Dependencies

### Edge Services

#### 1. Packet Capture Service
**Dependencies**: None (initial service)
**Outputs**:
- Raw packet data → MQTT topic
- Uses: MQTT publisher

**Start Order**: First

#### 2. Feature Extraction Service
**Dependencies**:
- Packet Capture Service (via MQTT topic)
- ids-mqtt package
- ids-schemas package

**Inputs**:
- `ids/edge/{node_id}/data/packets` MQTT topic

**Outputs**:
- Feature vectors → MQTT topic
- Uses: MQTT publisher

**Start Order**: Second

#### 3. ML Inference Service
**Dependencies**:
- Feature Extraction Service (via MQTT topic)
- ML models (ONNX)
- ids-mqtt package
- ids-schemas package

**Inputs**:
- Feature vectors → MQTT topic

**Outputs**:
- Inference results → MQTT topic
- Uses: MQTT publisher

**Start Order**: Third

#### 4. Device Monitor Service
**Dependencies**:
- Packet Capture Service (via MQTT topic)
- ids-mqtt package
- ids-schemas package

**Inputs**:
- ARP/DHCP packets → MQTT topic
- Local device database

**Outputs**:
- Device events → MQTT topic
- Uses: MQTT publisher

**Start Order**: Parallel with Feature Extraction

#### 5. Fusion Engine Service
**Dependencies**:
- ML Inference Service (via MQTT topic)
- Device Monitor Service (via MQTT topic)
- ids-mqtt package
- ids-schemas package

**Inputs**:
- ML predictions → MQTT topic
- Device events → MQTT topic

**Outputs**:
- Confirmed alerts → MQTT topic
- Uses: MQTT publisher

**Start Order**: Fourth

#### 6. MQTT Alert Service
**Dependencies**:
- Fusion Engine Service (via MQTT topic)
- Central MQTT broker
- ids-mqtt package

**Inputs**:
- Confirmed alerts → MQTT topic

**Outputs**:
- Central MQTT topics
- Uses: MQTT publisher

**Start Order**: Fifth

### Backend Services

#### 1. Dashboard API Service
**Dependencies**:
- PostgreSQL database
- Redis cache
- MQTT broker (for live updates)
- ids-schemas package
- ids-mqtt package

**Endpoints**:
- `/api/v1/alerts`
- `/api/v1/devices`
- `/api/v1/auth`
- `/api/v1/health`

**Start Order**: Second

#### 2. WebSocket Gateway Service
**Dependencies**:
- Redis (for pub/sub)
- MQTT broker
- ids-mqtt package

**Start Order**: Third

#### 3. Auth Service
**Dependencies**:
- PostgreSQL database
- Redis (for sessions)
- ids-schemas package

**Start Order**: Fourth

#### 4. Logging Service
**Dependencies**:
- Elasticsearch/Loki
- Docker logs

**Start Order**: Anytime

### Database Dependencies

```
┌─────────────────────────────────────────┐
│         PostgreSQL Database             │
├─────────────────────────────────────────┤
│  Alert → Device (FK)                    │
│  FlowRecord → Device (FK)               │
│  AuditLog → User (FK)                   │
└─────────────────────────────────────────┘
```

## Data Flow Diagrams

### Alert Flow

```
IoT Network
     │
     ▼
┌─────────────────────────────────────────┐
│  Packet Capture Service                 │
│  - Sniff network traffic                │
│  - Extract packet metadata              │
└──────────────────┬──────────────────────┘
                   │ MQTT: data/packets
                   ▼
┌─────────────────────────────────────────┐
│  Feature Extraction Service             │
│  - Build flow records                   │
│  - Extract ML features                  │
└──────────────────┬──────────────────────┘
                   │ MQTT: data/features
                   ▼
┌─────────────────────────────────────────┐
│  ML Inference Service                   │
│  - Load ONNX models                     │
│  - Run inference                        │
└──────────────────┬──────────────────────┘
                   │ MQTT: data/inference
                   ▼
┌─────────────────────────────────────────┐
│  Fusion Engine Service                  │
│  - Correlate signals                    │
│  - Apply thresholds                     │
└──────────────────┬──────────────────────┘
                   │ MQTT: alerts/high, critical
                   ▼
┌─────────────────────────────────────────┐
│  MQTT Alert Service                     │
│  - Publish to central broker            │
└──────────────────┬──────────────────────┘
                   │ MQTT: ids/alerts/critical
                   ▼
┌─────────────────────────────────────────┐
│  Backend Services                       │
│  - Dashboard API: Persist alerts        │
│  - WebSocket: Stream to frontend        │
└─────────────────────────────────────────┘
```

## Startup Order

### Development/Deployment

1. **Infrastructure**
   - PostgreSQL
   - Redis
   - MQTT Broker

2. **Edge Services**
   - Packet Capture
   - Feature Extraction
   - ML Inference
   - Device Monitor
   - Fusion Engine
   - MQTT Alert

3. **Backend Services**
   - Auth Service
   - Dashboard API
   - WebSocket Gateway

4. **Frontend**

### Docker Compose

```yaml
services:
  # Infrastructure first
  postgres:
  redis:
  mosquitto:
  
  # Edge services second
  packet-capture-service:
    depends_on:
      - mosquitto
  
  # Backend services third
  auth-service:
    depends_on:
      - postgres
  backend:
    depends_on:
      - postgres
      - redis
  websocket-gateway:
    depends_on:
      - redis
      - mosquitto
```

## Communication Patterns

### Synchronous
- Backend ↔ Database (SQLAlchemy async)
- Frontend ↔ Backend API (HTTP)

### Asynchronous
- Edge Services ↔ MQTT Broker
- Backend ↔ MQTT Broker
- WebSocket Gateway ↔ MQTT Broker
- Backend ↔ Redis (pub/sub)

### Event-Driven
- All services communicate via MQTT
- Decoupled architecture
- Automatic retry on failure
- QoS-based reliability

## Scaling Considerations

### Horizontal Scaling
- **Frontend**: Multiple instances + load balancer
- **Backend**: Multiple instances + database connection pooling
- **Edge**: Multiple Raspberry Pi nodes
- **MQTT**: Mosquitto clustering

### Vertical Scaling
- **Database**: Connection pooling + read replicas
- **Cache**: Redis replica set
- **Edge**: Resource limits per container

## Failure Patterns

### Service Failure
- Automatic restart (Docker restart policy)
- Health checks for liveness
- Circuit breakers for external dependencies

### Data Loss Prevention
- MQTT QoS 1 for alerts
- Database transactions with rollback
- Edge buffering when MQTT unavailable
- Backup jobs for critical data

### Network Partition
- MQTT offline buffering
- Local SQLite fallback
- Cache-first strategy
- Graceful degradation