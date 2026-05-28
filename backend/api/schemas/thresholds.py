from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class ThresholdBase(BaseModel):
    name: str
    value: float
    description: Optional[str] = None
    is_active: bool = True

class ThresholdCreate(ThresholdBase):
    pass

class ThresholdResponse(ThresholdBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
