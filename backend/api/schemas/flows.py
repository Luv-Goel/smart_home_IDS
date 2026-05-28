from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from .common import PaginationParams

class FlowBase(BaseModel):
    source_ip: str
    destination_ip: str
    source_port: int
    destination_port: int
    protocol: str
    bytes_sent: int
    bytes_received: int
    packets_sent: int
    packets_received: int

class FlowResponse(FlowBase):
    id: int
    start_time: datetime
    end_time: datetime
    is_anomalous: bool

    model_config = ConfigDict(from_attributes=True)

class FlowFilter(PaginationParams):
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    protocol: Optional[str] = None
    is_anomalous: Optional[bool] = None
