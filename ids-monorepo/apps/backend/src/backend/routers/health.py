"""Health check router for Smart Home IDS.

This module provides health check and metrics endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from backend.database import get_async_session

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "dashboard-api",
        "version": "1.0.0",
        "timestamp": None,
    }


@router.get("/health/database")
async def database_health(db: AsyncSession = Depends(get_async_session)):
    """Database health check.

    Args:
        db: Database session

    Returns:
        Database health status
    """
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": f"error: {str(e)}"}


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint.

    Returns:
        Metrics data
    """
    return {
        "service": "dashboard-api",
        "version": "1.0.0",
        "uptime_seconds": 0,
        "requests_total": 0,
        "requests_failed": 0,
        "inference_latency_p50": 0,
        "inference_latency_p95": 0,
        "inference_latency_p99": 0,
        "mqtt_connected": True,
        "db_pool_size": 10,
        "db_pool_active": 0,
    }


@router.get("/system/status")
async def system_status():
    """System status endpoint.

    Returns:
        System status
    """
    return {
        "status": "operational",
        "services": {
            "dashboard-api": "running",
            "websocket-gateway": "running",
            "mqtt-broker": "running",
            "database": "running",
        },
        "resources": {
            "cpu_percent": 0,
            "memory_percent": 0,
            "disk_percent": 0,
        },
        "alerts": {
            "total": 0,
            "active": 0,
            "critical": 0,
        },
    }