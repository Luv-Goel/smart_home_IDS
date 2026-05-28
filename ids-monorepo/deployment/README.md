# Deployment Infrastructure

This directory contains the deployment infrastructure and orchestration scripts for the IDS platform.

## Structure

* `infra/docker/` - Contains all `Dockerfile`s and the main `docker-compose.yml` for orchestrating the services.
* `infra/pi-config/` - Contains configuration files and overrides optimized for running on a Raspberry Pi / ARM64.
* `deployment/scripts/` - Scripts for deploying, starting, and stopping the application.
* `deployment/mosquitto/` - Stores Mosquitto configuration and data.

## Getting Started

1. Set up the `mosquitto` configuration by copying the default template.
   ```bash
   cp deployment/mosquitto/config/mosquitto.conf.example deployment/mosquitto/config/mosquitto.conf
   ```
2. Build and start the services using the deployment script:
   ```bash
   ./deployment/scripts/deploy.sh dev
   ```

## Raspberry Pi Deployment

For deploying on a Raspberry Pi, use the ARM64 overrides:

```bash
docker compose -f infra/docker/docker-compose.yml -f infra/pi-config/docker-compose.arm64.yml up -d
```

Review `infra/pi-config/README.md` for OS-level tuning options to minimize wear on the SD card and optimize memory.

## Included Services

The Docker Compose setup spins up the following services:

1. **PostgreSQL Database** (`ids-postgres`): Persistent storage for alerts, configuration, and long-term analytics.
2. **Redis** (`ids-redis`): Caching, pub/sub (optional), and rapid state storage.
3. **Mosquitto MQTT Broker** (`ids-mosquitto`): High-throughput event bus for IoT device messaging.
4. **Backend API** (`ids-backend`): FastAPI service handling business logic, rule processing, and API routes.
5. **WebSocket Gateway** (`ids-websocket-gateway`): Dedicated service handling real-time push notifications to clients.
6. **Frontend UI** (`ids-frontend`): React-based dashboard served via Nginx.
