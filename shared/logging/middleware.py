import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

from shared.logging.tracing import set_correlation_id

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI/Starlette middleware to add correlation IDs to requests and log them.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract correlation ID from header or generate a new one
        correlation_id = request.headers.get("X-Correlation-ID")
        set_correlation_id(correlation_id)

        start_time = time.perf_counter()

        # Log request start
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)

            # Calculate duration
            process_time = time.perf_counter() - start_time

            # Log request completion
            logger.info(
                "request_finished",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_s=round(process_time, 4),
            )

            # Include correlation ID in the response headers
            from shared.logging.tracing import get_correlation_id

            response.headers["X-Correlation-ID"] = get_correlation_id() or ""

            return response

        except Exception as exc:
            process_time = time.perf_counter() - start_time
            logger.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_s=round(process_time, 4),
                exc_info=exc,
            )
            raise
