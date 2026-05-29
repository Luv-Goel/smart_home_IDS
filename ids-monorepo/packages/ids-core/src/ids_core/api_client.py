"""Async API client for IDS services.

This module provides a robust async HTTP client with retry logic,
timeout handling, and structured error handling for all IDS services.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, TypeVar, Generic, Callable
from enum import Enum

import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientError
from structlog import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class HTTPMethod(Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class HTTPStatusCode(Enum):
    """HTTP status codes."""
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


@dataclass
class RetryConfig:
    """Retry configuration for API requests."""
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    exponential_backoff: bool = True
    retry_on_status: set = None
    
    def __post_init__(self):
        if self.retry_on_status is None:
            self.retry_on_status = {
                408,  # Request Timeout
                429,  # Too Many Requests
                502,  # Bad Gateway
                503,  # Service Unavailable
                504,  # Gateway Timeout
            }


@dataclass
class TimeoutConfig:
    """Timeout configuration for API requests."""
    total: float = 30.0  # Total timeout in seconds
    connect: float = 5.0  # Connection timeout in seconds
    sock_read: float = 30.0  # Socket read timeout in seconds
    sock_connect: float = 5.0  # Socket connect timeout in seconds


class APIError(Exception):
    """Base exception for API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response
    
    def __str__(self):
        if self.status_code:
            return f"APIError({self.status_code}): {self.message}"
        return f"APIError: {self.message}"


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""
    pass


class AuthenticationError(APIError):
    """Raised when authentication fails."""
    pass


class APIClient:
    """Async HTTP client with retry logic and error handling."""
    
    def __init__(
        self,
        base_url: str,
        session: Optional[ClientSession] = None,
        retry_config: Optional[RetryConfig] = None,
        timeout_config: Optional[TimeoutConfig] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        """Initialize API client.
        
        Args:
            base_url: Base URL for API requests
            session: Optional shared ClientSession
            retry_config: Retry configuration
            timeout_config: Timeout configuration
            default_headers: Default headers for all requests
        """
        self.base_url = base_url.rstrip("/")
        self._session = session
        self.retry_config = retry_config or RetryConfig()
        self.timeout_config = timeout_config or TimeoutConfig()
        self.default_headers = default_headers or {}
        
        # Create timeout object
        self.timeout = ClientTimeout(
            total=self.timeout_config.total,
            connect=self.timeout_config.connect,
            sock_read=self.timeout_config.sock_read,
            sock_connect=self.timeout_config.sock_connect,
        )
    
    async def request(
        self,
        method: HTTPMethod,
        endpoint: str,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict] = None,
    ) -> Dict:
        """Make HTTP request with retry logic.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (relative to base_url)
            data: Request body data
            headers: Additional headers
            params: Query parameters
            json: JSON data for POST/PUT requests
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            APIError: If request fails after retries
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_headers = {**self.default_headers, **(headers or {})}
        
        # Ensure JSON content type for JSON data
        if json is not None and "Content-Type" not in request_headers:
            request_headers["Content-Type"] = "application/json"
        
        session = self._session or await self._create_session()
        close_session = self._session is None
        
        try:
            response = await self._request_with_retry(
                session=session,
                method=method.value,
                url=url,
                data=data,
                headers=request_headers,
                params=params,
                json=json,
            )
            
            # Parse response
            if response.status == HTTPStatusCode.NO_CONTENT.value:
                return {}
            
            response_data = await response.json()
            
            # Check for error status
            if response.status >= 400:
                await self._handle_error_response(response, response_data)
            
            return response_data
            
        except ClientError as e:
            logger.error("Client error during API request", error=str(e), url=url)
            raise APIError(f"Client error: {str(e)}")
        finally:
            if close_session and session:
                await session.close()
    
    async def _request_with_retry(
        self,
        session: ClientSession,
        method: str,
        url: str,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make request with exponential backoff retry logic."""
        last_exception = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                start_time = asyncio.get_event_loop().time()
                
                async with session.request(
                    method=method,
                    url=url,
                    timeout=self.timeout,
                    **kwargs,
                ) as response:
                    # Log request metrics
                    elapsed = asyncio.get_event_loop().time() - start_time
                    logger.debug(
                        "API request completed",
                        method=method,
                        url=url,
                        status=response.status,
                        elapsed_ms=elapsed * 1000,
                        attempt=attempt + 1,
                    )
                    
                    # Check if we should retry
                    if (response.status in self.retry_config.retry_on_status and 
                        attempt < self.retry_config.max_retries):
                        
                        # Calculate delay with exponential backoff
                        delay = self._calculate_retry_delay(attempt)
                        logger.warning(
                            "Retrying request",
                            status=response.status,
                            attempt=attempt + 1,
                            max_retries=self.retry_config.max_retries,
                            delay_seconds=delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    
                    return response
                    
            except (ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                logger.warning(
                    "Request failed",
                    error=str(e),
                    attempt=attempt + 1,
                    max_retries=self.retry_config.max_retries,
                )
                
                if attempt < self.retry_config.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    await asyncio.sleep(delay)
        
        # If we get here, all retries failed
        error_msg = f"Request failed after {self.retry_config.max_retries} retries"
        logger.error(
            "All retries failed",
            error=str(last_exception),
            method=method,
            url=url,
        )
        raise APIError(f"{error_msg}: {str(last_exception)}")
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate delay for retry with exponential backoff."""
        if not self.retry_config.exponential_backoff:
            return self.retry_config.base_delay
        
        delay = self.retry_config.base_delay * (2 ** attempt)
        return min(delay, self.retry_config.max_delay)
    
    async def _create_session(self) -> ClientSession:
        """Create a new ClientSession."""
        return ClientSession(timeout=self.timeout)
    
    async def _handle_error_response(self, response, response_data):
        """Handle error response based on status code."""
        status = response.status
        
        if status == HTTPStatusCode.UNAUTHORIZED.value:
            raise AuthenticationError(
                message="Unauthorized",
                status_code=status,
                response=response_data,
            )
        elif status == HTTPStatusCode.FORBIDDEN.value:
            raise AuthenticationError(
                message="Forbidden",
                status_code=status,
                response=response_data,
            )
        elif status == 429:  # Rate limit
            raise RateLimitError(
                message="Rate limit exceeded",
                status_code=status,
                response=response_data,
            )
        else:
            error_message = response_data.get("detail", "Unknown error")
            raise APIError(
                message=error_message,
                status_code=status,
                response=response_data,
            )
    
    async def get(self, endpoint: str, **kwargs) -> Dict:
        """Perform GET request."""
        return await self.request(HTTPMethod.GET, endpoint, **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> Dict:
        """Perform POST request."""
        return await self.request(HTTPMethod.POST, endpoint, **kwargs)
    
    async def put(self, endpoint: str, **kwargs) -> Dict:
        """Perform PUT request."""
        return await self.request(HTTPMethod.PUT, endpoint, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> Dict:
        """Perform DELETE request."""
        return await self.request(HTTPMethod.DELETE, endpoint, **kwargs)
    
    async def patch(self, endpoint: str, **kwargs) -> Dict:
        """Perform PATCH request."""
        return await self.request(HTTPMethod.PATCH, endpoint, **kwargs)


class BaseServiceClient(APIClient):
    """Base client for specific IDS services."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialize service client.
        
        Args:
            api_key: Optional API key for authentication
            **kwargs: Additional arguments for APIClient
        """
        super().__init__(**kwargs)
        
        if api_key:
            self.default_headers["Authorization"] = f"Bearer {api_key}"
    
    async def health(self) -> Dict:
        """Check service health."""
        return await self.get("/health")
    
    async def metrics(self) -> Dict:
        """Get service metrics."""
        return await self.get("/metrics")