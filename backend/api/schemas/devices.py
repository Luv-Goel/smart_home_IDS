from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from .common import PaginationParams

class DeviceBase(BaseModel):
    mac_address: str
    ip_address: str
    hostname: Optional[str] = None
    device_type: Optional[str] = None

class DeviceResponse(DeviceBase):
    id: int
    first_seen: datetime
    last_seen: datetime
    is_trusted: bool
    is_blocked: bool

    model_config = ConfigDict(from_attributes=True)

class DeviceFilter(PaginationParams):
    is_trusted: Optional[bool] = None
    is_blocked: Optional[bool] = None
    device_type: Optional[str] = None
