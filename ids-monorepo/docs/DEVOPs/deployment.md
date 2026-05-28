# Deployment Guide

This guide covers deployment of Smart Home IDS in various environments.

## Table of Contents
1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Raspberry Pi Edge Deployment](#raspberry-pi-edge-deployment)
4. [Production Deployment](#production-deployment)

## Local Development

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### Setup

1. Clone the repository
```bash
git clone https://github.com/your-org/smart_home_IDS.git
cd smart_home_IDS/ids-monorepo
```

2. Start services
```bash
docker compose -f infra/docker/docker-compose.dev.yml up --build
```

3. Access services:
- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- PostgreSQL: `localhost:5432`

## Docker Deployment

### Production Setup

1. Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

2. Build and start:
```bash
docker compose -f infra/docker/docker-compose.yml build
docker compose -f infra/docker/docker-compose.yml up -d
```

3. View logs:
```bash
docker compose logs -f
```

4. Stop services:
```bash
docker compose down
```

## Raspberry Pi Edge Deployment

### Prerequisites
- Raspberry Pi 4/5 with 4GB RAM minimum
- Raspberry Pi OS Lite (64-bit)
- Docker & Docker Compose
- Network interface for monitoring

### Setup

1. Install Docker on Raspberry Pi:
```bash
curl -sSL https://get.docker.com | sh
sudo usermod -aG docker pi
```

2. Clone repository:
```bash
git clone https://github.com/your-org/smart_home_IDS.git
cd smart_home_IDS/ids-monorepo
```

3. Update `.env` with your configuration:
```bash
NODE_ID=pi-gateway-01
NETWORK_INTERFACE=eth0
```

4. Start edge services:
```bash
docker compose -f infra/docker/docker-compose.edge.yml up -d
```

### Raspberry Pi Optimization

The edge deployment includes:
- Lightweight Docker images
- Optimized for ARM64 architecture
- Reduced memory footprint
- CPU-optimized ML models
- Efficient packet processing

## Production Deployment

### High Availability Setup

1. Use Docker Swarm or Kubernetes for orchestration
2. Configure load balancing for backend services
3. Set up PostgreSQL replication
4. Enable TLS for all services
5. Configure monitoring and alerting

### Monitoring

- Prometheus metrics on port 9090
- Grafana dashboards in `infra/grafana/`
- Health check endpoints at `/health`
- Structured JSON logs

### Security Best Practices

1. Use secrets management for sensitive data
2. Enable TLS for all services
3. Configure network policies
4. Run containers as non-root
5. Regular security scans
6. Keep base images updated

## Troubleshooting

### Common Issues

1. **Port conflicts**
   ```bash
   docker compose ps
   # Check for port conflicts and adjust ports in docker-compose.yml
   ```

2. **Database connection issues**
   ```bash
   docker compose exec postgres pg_isready
   # Check database health
   ```

3. **MQTT connection issues**
   ```bash
   docker compose logs mosquitto
   # Check MQTT broker logs
   ```

### Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f packet-capture-service
```

### Reset System

```bash
# Stop and remove all containers
docker compose down

# Remove volumes (be careful!)
docker compose down -v

# Rebuild and start
docker compose up --build
```