from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from ..dependencies.database import get_db

router = APIRouter()

@router.get("/")
async def get_metrics(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get system and detection metrics.
    """
    return {
        "total_alerts": 0,
        "active_devices": 0,
        "flows_processed": 0,
        "system_status": "healthy"
    }
