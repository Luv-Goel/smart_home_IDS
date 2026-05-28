"""Base model and common schema utilities for Smart Home IDS.

This module provides the base Pydantic model and common utilities
used across all schemas.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict
from pydantic.json_schema import models_json_schema


T = TypeVar('T')


class IDSBasemodel(BaseModel):
    """Base model for all IDS schemas.

    Provides common functionality like timestamp, ID, and serialization utilities.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        extra="allow",
    )

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")


class PaginationRequest(BaseModel):
    """Pagination request model."""

    limit: int = Field(default=50, ge=1, le=1000, description="Number of records per page")
    offset: int = Field(default=0, ge=0, description="Number of records to skip")
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")


class PaginationResponse(BaseModel, Generic[T]):
    """Pagination response model."""

    total: int = Field(description="Total number of records")
    limit: int = Field(description="Number of records per page")
    offset: int = Field(description="Number of records skipped")
    data: list[T] = Field(description="List of records")


class EventEnvelope(IDSBasemodel):
    """Event envelope for message queue communication."""

    event_id: UUID = Field(description="Unique event identifier")
    event_type: str = Field(description="Type of event")
    timestamp: datetime = Field(description="Event timestamp")
    source: str = Field(description="Source of the event")
    payload: dict[str, Any] = Field(description="Event payload")


class ResponseModel(IDSBasemodel):
    """Standard API response model."""

    success: bool = Field(description="Whether the request was successful")
    message: str | None = Field(default=None, description="Response message")
    data: dict[str, Any] | list[Any] | None = Field(default=None, description="Response data")
    error: dict[str, Any] | None = Field(default=None, description="Error information if any")