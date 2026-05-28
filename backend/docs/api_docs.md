# Smart Home IDS API Documentation

This API provides the backend services for the Smart Home Intrusion Detection System. It is built with FastAPI and provides endpoints for managing alerts, devices, flows, metrics, and thresholds.

## Endpoints

### Health
- `GET /api/health`
  - Returns the health status and version of the API.

### Alerts
- `GET /api/alerts`
  - Returns a paginated list of alerts.
  - Supports filtering by `severity`, `is_resolved`, `start_time`, and `end_time`.

### Devices
- `GET /api/devices`
  - Returns a paginated list of connected devices.
  - Supports filtering by `is_trusted`, `is_blocked`, and `device_type`.

### Flows
- `GET /api/flows`
  - Returns a paginated list of network flows.
  - Supports filtering by `source_ip`, `destination_ip`, `protocol`, and `is_anomalous`.

### Metrics
- `GET /api/metrics`
  - Returns system and detection metrics.

### Thresholds
- `POST /api/thresholds`
  - Creates a new detection threshold.
  - Requires `name` and `value`. Optionally accepts `description` and `is_active`.

## WebSockets
- `WS /ws/alerts`
  - Provides a real-time stream of alerts and system events.

## Features Included
- **Pagination**: Standardized paginated responses for lists.
- **Filtering**: Query parameters available on list endpoints.
- **Async DB Access**: Database interactions via `sqlalchemy.ext.asyncio`.
- **Validation**: Schema validation using Pydantic V2.
- **OpenAPI Docs**: Automatically generated documentation at `/api/docs` and `/api/redoc`.
