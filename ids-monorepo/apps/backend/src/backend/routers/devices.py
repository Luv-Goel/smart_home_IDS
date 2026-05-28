"""Device router for Smart Home IDS.

This module provides API endpoints for device management.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.database import get_async_session, Device
from ids_schemas.device import DeviceQueryParams, DeviceType, DeviceState

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


@router.get("/", response_model=List[Device])
async def list_devices(
    params: DeviceQueryParams = Depends(),
    db: AsyncSession = Depends(get_async_session),
):
    """List devices with filtering.

    Args:
        params: Query parameters
        db: Database session

    Returns:
        List of devices
    """
    query = select(Device)

    # Apply filters
    if params.mac_address:
        query = query.where(Device.mac_address == params.mac_address)
    if params.ip_address:
        query = query.where(Device.ip_address == params.ip_address)
    if params.device_type:
        query = query.where(Device.device_type.in_(params.device_type))
    if params.is_trusted is not None:
        query = query.where(Device.is_trusted == params.is_trusted)
    if params.is_blocked is not None:
        query = query.where(Device.is_blocked == params.is_blocked)
    if params.state:
        query = query.where(Device.state.in_(params.state))

    query = query.order_by(Device.last_seen.desc())
    query = query.offset((params.page - 1) * params.page_size).limit(params.page_size)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{device_id}", response_model=Device)
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    """Get device by ID (MAC address).

    Args:
        device_id: Device MAC address
        db: Database session

    Returns:
        Device details
    """
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return device


@router.patch("/{device_id}/trust")
async def trust_device(
    device_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    """Trust a device.

    Args:
        device_id: Device MAC address
        db: Database session

    Returns:
        Updated device
    """
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.is_trusted = True
    device.is_blocked = False

    await db.commit()
    await db.refresh(device)

    return device


@router.patch("/{device_id}/block")
async def block_device(
    device_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    """Block a device.

    Args:
        device_id: Device MAC address
        db: Database session

    Returns:
        Updated device
    """
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.is_blocked = True
    device.is_trusted = False

    await db.commit()
    await db.refresh(device)

    return device


@router.patch("/{device_id}/untrust")
async def untrust_device(
    device_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    """Remove trust from a device.

    Args:
        device_id: Device MAC address
        db: Database session

    Returns:
        Updated device
    """
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.is_trusted = False

    await db.commit()
    await db.refresh(device)

    return device


@router.patch("/{device_id}/unblock")
async def unblock_device(
    device_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    """Unblock a device.

    Args:
        device_id: Device MAC address
        db: Database session

    Returns:
        Updated device
    """
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.is_blocked = False

    await db.commit()
    await db.refresh(device)

    return device


@router.get("/analytics/breakdown")
async def get_device_breakdown(
    db: AsyncSession = Depends(get_async_session),
):
    """Get device type breakdown.

    Args:
        db: Database session

    Returns:
        Device type counts
    """
    query = select(
        Device.device_type,
        func.count().label("count")
    ).group_by(Device.device_type)

    result = await db.execute(query)
    data = result.fetchall()
    return {row.device_type: row.count for row in data}


@router.get("/analytics/trusted-count")
async def get_trusted_count(
    db: AsyncSession = Depends(get_async_session),
):
    """Get count of trusted devices.

    Args:
        db: Database session

    Returns:
        Trusted device count
    """
    query = select(func.count()).where(Device.is_trusted == True)
    result = await db.execute(query)
    return {"trusted_count": result.scalar_one()}


@router.get("/analytics/blocked-count")
async def get_blocked_count(
    db: AsyncSession = Depends(get_async_session),
):
    """Get count of blocked devices.

    Args:
        db: Database session

    Returns:
        Blocked device count
    """
    query = select(func.count()).where(Device.is_blocked == True)
    result = await db.execute(query)
    return {"blocked_count": result.scalar_one()}