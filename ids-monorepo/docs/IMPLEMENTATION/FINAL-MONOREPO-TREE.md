# Final Monorepo Tree Structure

This is the complete directory structure of Smart Home IDS monorepo.

## Complete File Tree

```
smart_home_IDS/
├── README.md                                              # Project overview
├── ids-monorepo/
│   ├── README.md                                          # Monorepo overview
│   ├── pyproject.toml                                     # Poetry configuration
│   ├── .pre-commit-config.yaml                           # Pre-commit hooks
│   ├── .github/
│   │   └── workflows/
│   │       ├── test.yml                                  # Test workflow
│   │       ├── lint.yml                                  # Lint workflow
│   │       └── build.yml                                 # Build workflow
│   ├── .gitignore
│   ├── .env.example                                       # Environment template
│   ├── infra/
│   │   └── docker/
│   │       ├── Dockerfile.backend                        # Backend container
│   │       ├── Dockerfile.edge                          # Edge container
│   │       ├── Dockerfile.frontend                      # Frontend container
│   │       ├── Dockerfile.websocket                     # WebSocket gateway
│   │       ├── docker-compose.yml                       # Full compose file
│   │       └── mosquitto/
│   │           ├── config/
│   │           │   ├── mosquitto.conf                   # MQTT config
│   │           │   └── acl.conf                         # Access control
│   │           └── data/                                 # Data directory
│   ├── apps/
│   │   ├── backend/
│   │   │   ├── pyproject.toml                           # Backend dependencies
│   │   │   ├── requirements.txt                         # Requirements file
│   │   │   └── src/
│   │   │       └── backend/
│   │   │           ├── __init__.py                      # Package init
│   │   │           ├── main.py                          # FastAPI app entry
│   │   │           ├── config.py                        # Config management
│   │   │           ├── database/
│   │   │           │   ├── __init__.py                  # DB package init
│   │   │           │   ├── config.py                    # DB config
│   │   │           │   ├── session.py                   # Session management
│   │   │           │   └── models.py                    # SQLAlchemy models
│   │   │           ├── routers/
│   │   │           │   ├── __init__.py                  # Routers package
│   │   │           │   ├── alerts.py                    # Alert endpoints
│   │   │           │   ├── devices.py                   # Device endpoints
│   │   │           │   ├── auth.py                      # Auth endpoints
│   │   │           │   └── health.py                    # Health endpoints
│   │   │           ├── services/                        # Business logic
│   │   │           ├── middleware/                      # Middleware
│   │   │           └── utils/                           # Utilities
│   │   ├── frontend/
│   │   │   ├── pyproject.toml                           # Frontend dependencies
│   │   │   ├── package.json                             # NPM dependencies
│   │   │   ├── tsconfig.json                            # TypeScript config
│   │   │   ├── tsconfig.node.json                       # Node TypeScript config
│   │   │   ├── vite.config.ts                           # Vite configuration
│   │   │   ├── tailwind.config.js                       # Tailwind config
│   │   │   ├── postcss.config.js                        # PostCSS config
│   │   │   └── src/
│   │   │       ├── main.tsx                             # Entry point
│   │   │       ├── app.tsx                              # Main router
│   │   │       ├── index.css                            # Global styles
│   │   │       ├── lib/
│   │   │       │   └── utils.ts                         # Utility functions
│   │   │       ├── components/                          # UI components
│   │   │       ├── layouts/
│   │   │       │   ├── layout.tsx                       # Main layout
│   │   │       │   ├── header.tsx                       # Header component
│   │   │       │   ├── sidebar.tsx                      # Sidebar component
│   │   │       │   └── footer.tsx                       # Footer component
│   │   │       ├── pages/
│   │   │       │   ├── dashboard.tsx                    # Dashboard page
│   │   │       │   ├── alerts.tsx                       # Alerts page
│   │   │       │   ├── devices.tsx                      # Devices page
│   │   │       │   ├── models.tsx                       # Models page
│   │   │       │   └── settings.tsx                     # Settings page
│   │   │       ├── hooks/                               # Custom hooks
│   │   │       └── store/                               # Zustand stores
│   │   └── edge/                                        # Edge services (skeleton)
│   ├── packages/
│   │   ├── ids-core/
│   │   │   ├── pyproject.toml                           # Core dependencies
│   │   │   └── src/
│   │   │       └── ids_core/
│   │   │           ├── __init__.py                      # Package init
│   │   │           ├── config.py                        # Settings
│   │   │           ├── logger.py                        # Structlog setup
│   │   │           └── utils.py                         # Utilities
│   │   ├── ids-schemas/
│   │   │   ├── pyproject.toml                           # Schemas dependencies
│   │   │   └── src/
│   │   │       └── ids_schemas/
│   │   │           ├── __init__.py                      # Package init
│   │   │           ├── base.py                          # Base models
│   │   │           ├── alert.py                         # Alert schemas
│   │   │           ├── device.py                        # Device schemas
│   │   │           ├── flow.py                          # Flow schemas
│   │   │           ├── health.py                        # Health schemas
│   │   │           ├── inference.py                     # Inference schemas
│   │   │           └── auth.py                          # Auth schemas
│   │   ├── ids-mqtt/
│   │   │   ├── pyproject.toml                           # MQTT dependencies
│   │   │   └── src/
│   │   │       └── ids_mqtt/
│   │   │           ├── __init__.py                      # Package init
│   │   │           ├── topic.py                         # Topic registry
│   │   │           ├── client.py                        # MQTT client
│   │   │           ├── publisher.py                     # Publisher
│   │   │           └── subscriber.py                    # Subscriber
│   │   ├── ids-models/                                  # Database models
│   │   └── ids-ml-plugins/                              # ML interface
│   ├── services/
│   │   ├── packet-capture-service/
│   │   │   ├── pyproject.toml                           # Dependencies
│   │   │   ├── requirements.txt                         # Requirements
│   │   │   └── src/
│   │   │       └── packet_capture_service/
│   │   │           ├── __init__.py                      # Package init
│   │   │           ├── main.py                          # Service entry
│   │   │           └── service.py                       # Main service class
│   │   ├── feature-extraction-service/
│   │   │   ├── pyproject.toml                           # Dependencies
│   │   │   ├── requirements.txt                         # Requirements
│   │   │   └── src/
│   │   │       └── feature_extraction_service/
│   │   │           ├── __init__.py                      # Package init
│   │   │           └── service.py                       # Main service class
│   │   ├── ml-inference-service/                        # Skeleton
│   │   ├── device-monitor-service/                      # Skeleton
│   │   └── fusion-engine-service/                       # Skeleton
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                                  # Pytest fixtures
│   │   ├── backend/
│   │   │   ├── __init__.py
│   │   │   └── test_api.py                              # API tests
│   │   ├── frontend/
│   │   │   ├── __init__.py
│   │   │   └── test_components.tsx                      # Component tests
│   │   └── edge/
│   │       ├── __init__.py
│   │       └── test_services.py                         # Service tests
│   ├── docs/
│   │   ├── ARCHITECTURE/
│   │   │   └── system-architecture.md                   # Architecture docs
│   │   ├── DEVOPs/
│   │   │   └── deployment.md                            # Deployment guide
│   │   ├── EDGE/
│   │   │   └── raspberry-pi-setup.md                    # Pi setup guide
│   │   ├── IMPLEMENTATION/
│   │   │   ├── IMPLEMENTATION-CHECKLIST.md              # Implementation status
│   │   │   ├── DEPENDENCY-GRAPH.md                      # Service dependencies
│   │   │   └── FINAL-MONOREPO-TREE.md                   # This file
│   │   └── backend/
│   │       └── development.md                           # Backend guide
│   └── scripts/                                         # Utility scripts
└── services/                                            # Edge services (alternate location)
```

## Service Port Mapping

| Service | Port | Type |
|---------|------|------|
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache/Queue |
| Mosquitto MQTT | 1883 | Message Broker |
| Mosquitto WebSocket | 9001 | WS Bridge |
| Backend API | 8000 | REST API |
| WebSocket Gateway | 8001 | WebSocket |
| Frontend | 5173 | React App |

## Package Dependencies

```
ids-schemas
   ↓ imports
ids-mqtt
   ↓ imports
ids-core

backend
   ↓ imports
ids-core, ids-schemas, ids-mqtt
   ↓ runs on
PostgreSQL, Redis, MQTT

packet-capture-service
   ↓ imports
ids-core, ids-schemas, ids-mqtt
   ↓ runs on
Edge (Raspberry Pi)

feature-extraction-service
   ↓ imports
ids-core, ids-schemas, ids-mqtt
   ↓ runs on
Edge (Raspberry Pi)

ml-inference-service
   ↓ imports
ids-core, ids-schemas, ids-mqtt
   ↓ runs on
Edge (Raspberry Pi)
```

## File Count Summary

| Directory | Files | Lines of Code |
|-----------|-------|---------------|
| ids-monorepo/root | 8 | ~400 |
| packages/ | 18 | ~2,500 |
| apps/backend/src | 15 | ~1,800 |
| apps/frontend/src | 25 | ~2,200 |
| services/ | 8 | ~800 |
| docs/ | 12 | ~3,000 |
| infra/docker/ | 12 | ~500 |
| .github/workflows/ | 3 | ~300 |
| **Total** | **101+** | **~11,500+** |

## Build Dependencies Graph

```
Backend Build:
ids-schemas → ids-mqtt → ids-core → backend

Edge Build:
ids-schemas → ids-mqtt → ids-core → packet-capture-service
ids-schemas → ids-mqtt → ids-core → feature-extraction-service
ids-schemas → ids-mqtt → ids-core → ml-inference-service

Frontend Build:
TypeScript → Vite → Tailwind → React
```

## Deployment Dependencies

```
Infrastructure Layer:
PostgreSQL ← Redis ← MQTT

Edge Layer:
Packet Capture ← Feature Extraction ← ML Inference
                                             ↑
Device Monitor ← Fusion Engine ← MQTT Alert ┘
                                             ↓
Backend Layer:                               MQTT Broker
Dashboard API ← WebSocket Gateway ───────────┘
        ↑
Auth Service ← Redis

Frontend ← Dashboard API
```

## Next Steps for Implementation Agents

1. **Review the dependency graph**
2. **Set up local development environment**
3. **Implement their assigned service**
4. **Write unit and integration tests**
5. **Update documentation**
6. **Create PR with tests passing**

## Development Commands

```bash
# Install dependencies
cd ids-monorepo
poetry install

# Start infrastructure
docker compose -f infra/docker/docker-compose.yml up -d

# Run backend
cd apps/backend
poetry run uvicorn backend.main:app --reload

# Run frontend
cd apps/frontend
npm install
npm run dev

# Run tests
poetry run pytest tests/
```