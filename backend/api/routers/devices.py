from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..schemas.devices import DeviceResponse, DeviceFilter
from ..schemas.common import PaginationParams, PaginatedResponse
from ..dependencies.database import get_db

router = APIRouter()

@router.get("/", response_model=PaginatedResponse[DeviceResponse])
async def get_devices(
    params: PaginationParams = Depends(),
    is_trusted: Optional[bool] = Query(None),
    is_blocked: Optional[bool] = Query(None),
    device_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a paginated list of devices with optional filtering.
    """
    return PaginatedResponse(
        data=[],
        total=0,
        page=params.page,
        size=params.size,
        pages=0
    )
