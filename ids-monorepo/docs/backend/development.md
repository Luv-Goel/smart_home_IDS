# Backend Development Guide

This guide covers backend development for Smart Home IDS.

## Architecture

The backend follows a layered architecture:

```
┌─────────────────────────────────────────┐
│           API Layer (FastAPI)           │
├─────────────────────────────────────────┤
│       Service Layer (Business Logic)    │
├─────────────────────────────────────────┤
│        Repository Layer (ORM)           │
├─────────────────────────────────────────┤
│          Database (PostgreSQL)          │
└─────────────────────────────────────────┘
```

## Project Structure

```
apps/backend/src/backend/
├── main.py                      # FastAPI application entry point
├── config.py                    # Configuration management
├── database/
│   ├── __init__.py
│   ├── config.py                # Database configuration
│   ├── session.py               # Session management
│   └── models.py                # SQLAlchemy models
├── routers/
│   ├── __init__.py
│   ├── alerts.py                # Alert endpoints
│   ├── devices.py               # Device endpoints
│   ├── auth.py                  # Authentication endpoints
│   └── health.py                # Health check endpoints
├── services/                    # Business logic services
│   ├── alert_service.py
│   ├── device_service.py
│   └── ml_service.py
├── middleware/                  # Middleware components
│   ├── auth.py
│   ├── rate_limit.py
│   └── logging.py
└── utils/
    └── security.py
```

## Database Models

### Device Model

Tracks IoT devices in the network:

```python
class Device(Base):
    id = Column(String, primary_key=True)  # MAC Address
    ip_address = Column(String)
    device_type = Column(String)
    is_trusted = Column(Boolean)
    is_blocked = Column(Boolean)
```

### Alert Model

Stores detected threats:

```python
class Alert(Base):
    device_id = Column(String, ForeignKey('devices.id'))
    alert_type = Column(String)
    severity = Column(Enum(AlertSeverity))
    confidence = Column(Float)
    payload = Column(JSON)
```

## API Endpoints

### Authentication

- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/register` - Register
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Get current user

### Alerts

- `GET /api/v1/alerts` - List alerts
- `GET /api/v1/alerts/{alert_id}` - Get alert
- `PATCH /api/v1/alerts/{alert_id}/resolve` - Resolve alert
- `POST /api/v1/alerts/events` - Receive alert event (edge)

### Devices

- `GET /api/v1/devices` - List devices
- `GET /api/v1/devices/{device_id}` - Get device
- `PATCH /api/v1/devices/{device_id}/trust` - Trust device
- `PATCH /api/v1/devices/{device_id}/block` - Block device

### Health

- `GET /api/v1/health` - Health check
- `GET /api/v1/metrics` - Prometheus metrics
- `GET /api/v1/system/status` - System status

## Service Layer

### Alert Service

```python
class AlertService:
    async def create_alert(self, db: AsyncSession, alert_data: dict) -> Alert:
        """Create a new alert."""
    
    async def get_alerts(self, db: AsyncSession, filters: dict) -> list[Alert]:
        """Get alerts with filtering."""
    
    async def resolve_alert(self, db: AsyncSession, alert_id: int) -> Alert:
        """Resolve an alert."""
```

### Device Service

```python
class DeviceService:
    async def create_device(self, db: AsyncSession, device_data: dict) -> Device:
        """Create a new device."""
    
    async def update_device(self, db: AsyncSession, device_id: str, updates: dict) -> Device:
        """Update device information."""
    
    async def block_device(self, db: AsyncSession, device_id: str) -> Device:
        """Block a device."""
```

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/ids

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ACCESS_TOKEN_EXPIRES=900

# Server
API_HOST=0.0.0.0
API_PORT=8000
```

### Config Files

Create `config.yaml`:

```yaml
database:
  pool_size: 10
  max_overflow: 20
auth:
  jwt_secret_key: ${JWT_SECRET_KEY}
  token_expires: 900
```

## Testing

### Unit Tests

```bash
# Run backend tests
poetry run pytest apps/backend/tests/
```

### API Tests

```python
def test_create_alert(client: TestClient):
    response = client.post("/api/v1/alerts", json={
        "alert_type": "DDoS",
        "severity": "HIGH",
    })
    assert response.status_code == 201
```

### Integration Tests

```python
async def test_alert_lifecycle():
    # Create alert
    # Query alerts
    # Resolve alert
    # Verify state
```

## Logging

```python
from backend.main import logger

logger.info("Processing alert", alert_type="DDoS")
logger.error("Failed to create alert", error=str(e))
```

## Docker

### Build Backend Image

```bash
docker build -f infra/docker/Dockerfile.backend -t ids-backend .
```

### Run Backend

```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/ids \
  ids-backend
```

## Best Practices

1. **Database**: Use async sessions, avoid N+1 queries
2. **API**: Follow REST conventions, proper status codes
3. **Security**: Validate inputs, use parameterized queries
4. **Testing**: Write unit and integration tests
5. **Logging**: Use structured logging, include context
6. **Configuration**: Use environment variables, validate configs

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker compose ps postgres

# Test connection
pg_isready -U idsteam
```

### Slow Queries

```python
# Enable query logging
SQLALCHEMY_ECHO=true
```

### Memory Issues

```bash
# Check container memory
docker stats ids-backend
```

## Performance Optimization

1. Use SQLAlchemy connection pooling
2. Index frequently queried columns
3. Use async operations for I/O
4. Cache frequently accessed data
5. Optimize JSON serialization