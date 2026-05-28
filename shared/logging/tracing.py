import uuid
import contextvars
from typing import Optional

# Context variable to hold the current correlation ID
correlation_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)


def get_correlation_id() -> Optional[str]:
    """Retrieve the current correlation ID from the context."""
    return correlation_id_ctx.get()


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set the correlation ID in the context.
    If none is provided, generate a new UUID.
    Returns the set correlation ID.
    """
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    correlation_id_ctx.set(correlation_id)
    return correlation_id


def structlog_add_correlation_id(logger, log_method, event_dict):
    """
    structlog processor to add correlation_id to log events.
    """
    req_id = get_correlation_id()
    if req_id:
        event_dict["correlation_id"] = req_id
    return event_dict
