from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from .common import PaginationParams, PaginatedResponse

class AlertBase(BaseModel):
    alert_type: str
    severity: str
    description: str
    source_ip: str
    destination_ip: str
    metadata: Optional[Dict[str, Any]] = None

class AlertCreate(AlertBase):
    pass

class AlertResponse(AlertBase):
    id: int
    timestamp: datetime
    is_resolved: bool

    model_config = ConfigDict(from_attributes=True)

class AlertFilter(PaginationParams):
    severity: Optional[str] = None
    is_resolved: Optional[bool] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
