"""Alert router for Smart Home IDS.

This module provides API endpoints for alert management.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from backend.database import get_async_session, Alert
from ids_schemas.alert import (
    AlertEvent,
    AlertQueryParams,
    AlertSeverity,
    AlertCategory,
)

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("/", response_model=List[Alert])
async def list_alerts(
    params: AlertQueryParams = Depends(),
    db: AsyncSession = Depends(get_async_session),
):
    """List alerts with filtering.

    Args:
        params: Query parameters
        db: Database session

    Returns:
        List of alerts
    """
    query = select(Alert).options(selectinload(Alert.device))

    # Apply filters
    if params.start_time:
        query = query.where(Alert.timestamp >= datetime.fromisoformat(params.start_time))
    if params.end_time:
        query = query.where(Alert.timestamp <= datetime.fromisoformat(params.end_time))
    if params.severity:
        query = query.where(Alert.severity.in_(params.severity))
    if params.category:
        query = query.where(Alert.category.in_(params.category))
    if params.device_id:
        query = query.where(Alert.device_id == params.device_id)
    if params.node_id:
        query = query.where(Alert.edge_node_id == params.node_id)
    if params.is_resolved is not None:
        query = query.where(Alert.is_resolved == params.is_resolved)

    query = query.order_by(Alert.timestamp.desc())
    query = query.offset((params.page - 1) * params.page_size).limit(params.page_size)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{alert_id}", response_model=Alert)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Get alert by ID.

    Args:
        alert_id: Alert ID
        db: Database session

    Returns:
        Alert details
    """
    query = select(Alert).options(selectinload(Alert.device)).where(Alert.id == alert_id)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert


@router.patch("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    notes: str = Query(default=None, description="Resolution notes"),
    db: AsyncSession = Depends(get_async_session),
):
    """Resolve an alert.

    Args:
        alert_id: Alert ID
        notes: Resolution notes
        db: Database session

    Returns:
        Updated alert
    """
    query = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    alert.notes = notes or alert.notes

    await db.commit()
    await db.refresh(alert)

    return alert


@router.patch("/{alert_id}/false-positive")
async def mark_false_positive(
    alert_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Mark alert as false positive.

    Args:
        alert_id: Alert ID
        db: Database session

    Returns:
        Updated alert
    """
    query = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_false_positive = True
    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()

    await db.commit()
    await db.refresh(alert)

    return alert


@router.get("/analytics/critical-count")
async def get_critical_count(
    db: AsyncSession = Depends(get_async_session),
):
    """Get count of critical alerts.

    Args:
        db: Database session

    Returns:
        Critical alert count
    """
    query = select(func.count()).where(Alert.severity == AlertSeverity.CRITICAL)
    result = await db.execute(query)
    return {"critical_count": result.scalar_one()}


@router.get("/analytics/severity-breakdown")
async def get_severity_breakdown(
    db: AsyncSession = Depends(get_async_session),
):
    """Get severity breakdown.

    Args:
        db: Database session

    Returns:
        Severity breakdown counts
    """
    query = select(
        Alert.severity,
        func.count().label("count")
    ).group_by(Alert.severity)

    result = await db.execute(query)
    data = result.fetchall()
    return {row.severity: row.count for row in data}


@router.post("/events", status_code=201)
async def receive_alert_event(
    event: AlertEvent,
    db: AsyncSession = Depends(get_async_session),
):
    """Receive alert event from edge node.

    Args:
        event: Alert event
        db: Database session

    Returns:
        Success message
    """
    alert = Alert(
        edge_node_id=event.node_id,
        device_id=event.device_id,
        alert_type=event.payload.alert_type,
        category=event.payload.category,
        severity=event.payload.severity,
        confidence=event.payload.confidence_score,
        description=event.payload.description,
        payload=event.payload.dict(exclude={"category", "severity"}),
        source_ip=event.payload.source_ip,
        destination_ip=event.payload.destination_ip,
        source_mac=event.payload.source_mac,
        destination_mac=event.payload.destination_mac,
        timestamp=event.payload.timestamp,
        ml_metadata=event.payload.ml_metadata,
    )

    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    return {"status": "success", "alert_id": alert.id}