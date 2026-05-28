#!/bin/bash
set -e

echo "Starting deployment process..."

# Default environment is development
ENV=${1:-dev}

# Validate environment
if [[ ! "$ENV" =~ ^(dev|prod)$ ]]; then
    echo "Invalid environment specified. Use 'dev' or 'prod'."
    return 1 2>/dev/null || true
fi

echo "Deploying for environment: $ENV"

# Build containers
echo "Building containers..."
docker compose -f infra/docker/docker-compose.yml build

# Start services
echo "Starting services..."
docker compose -f infra/docker/docker-compose.yml up -d

echo "Deployment completed successfully!"
