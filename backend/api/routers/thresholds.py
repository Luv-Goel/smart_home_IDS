from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.thresholds import ThresholdCreate, ThresholdResponse
from ..dependencies.database import get_db

router = APIRouter()

@router.post("/", response_model=ThresholdResponse, status_code=status.HTTP_201_CREATED)
async def create_threshold(
    threshold: ThresholdCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new detection threshold.
    """
    from datetime import datetime, timezone

    # Mock response
    return ThresholdResponse(
        id=1,
        name=threshold.name,
        value=threshold.value,
        description=threshold.description,
        is_active=threshold.is_active,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
