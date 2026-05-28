"""Utility functions for Smart Home IDS.

This module provides common utility functions used across all services.
"""

import asyncio
import json
import hashlib
import os
import random
import re
import string
import time
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar, cast

import aiofiles
from pydantic import BaseModel

from ids_core.logger import get_logger

logger = get_logger("ids_core.utils")

T = TypeVar('T')


def generate_unique_id(prefix: str = "id") -> str:
    """Generate a unique ID string.

    Args:
        prefix: Optional prefix for the ID.

    Returns:
        A unique ID string.
    """
    timestamp = int(time.time() * 1000)
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}_{timestamp}_{random_str}"


def generate_mac_address() -> str:
    """Generate a random MAC address.

    Returns:
        A MAC address in format XX:XX:XX:XX:XX:XX.
    """
    return ":".join(["{:02x}".format(random.randint(0, 255)) for _ in range(6)])


def hash_sha256(data: str | bytes) -> str:
    """Compute SHA256 hash of data.

    Args:
        data: String or bytes to hash.

    Returns:
        Hexadecimal hash string.
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


async def read_file_async(filepath: str) -> str:
    """Read file asynchronously.

    Args:
        filepath: Path to the file.

    Returns:
        File contents as string.
    """
    async with aiofiles.open(filepath, 'r') as f:
        return await f.read()


async def write_file_async(filepath: str, content: str) -> None:
    """Write content to file asynchronously.

    Args:
        filepath: Path to the file.
        content: Content to write.
    """
    async with aiofiles.open(filepath, 'w') as f:
        await f.write(content)


def parse_timestamp(timestamp: str | None = None) -> str:
    """Parse and format timestamp to ISO format.

    Args:
        timestamp: Optional timestamp string. If None, uses current time.

    Returns:
        ISO formatted timestamp string.
    """
    if timestamp is None:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.isoformat()
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc).isoformat()


def validate_mac_address(mac: str) -> bool:
    """Validate MAC address format.

    Args:
        mac: MAC address string.

    Returns:
        True if valid, False otherwise.
    """
    pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    return bool(re.match(pattern, mac))


def validate_ip_address(ip: str) -> bool:
    """Validate IPv4 address format.

    Args:
        ip: IP address string.

    Returns:
        True if valid, False otherwise.
    """
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    parts = ip.split('.')
    return all(0 <= int(part) <= 255 for part in parts)


async def run_async(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run synchronous function in async context.

    Args:
        func: Synchronous function to run.
        *args: Positional arguments for the function.
        **kwargs: Keyword arguments for the function.

    Returns:
        Result of the function.
    """
    return await asyncio.to_thread(func, *args, **kwargs)


def model_to_dict(model: BaseModel) -> dict[str, Any]:
    """Convert Pydantic model to dictionary.

    Args:
        model: Pydantic model instance.

    Returns:
        Dictionary representation of the model.
    """
    return model.model_dump(exclude_unset=True)


def model_to_json(model: BaseModel, indent: int | None = None) -> str:
    """Convert Pydantic model to JSON string.

    Args:
        model: Pydantic model instance.
        indent: Optional indentation for pretty printing.

    Returns:
        JSON string representation of the model.
    """
    return model.model_dump_json(exclude_unset=True, indent=indent)


def create_sequential_id(prefix: str, start: int = 1) -> Callable[[], str]:
    """Create a sequential ID generator.

    Args:
        prefix: Prefix for generated IDs.
        start: Starting number.

    Returns:
        A function that generates sequential IDs.
    """
    count = start - 1

    def generator() -> str:
        nonlocal count
        count += 1
        return f"{prefix}_{count}"

    return generator


def safe_get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary values.

    Args:
        data: Dictionary to retrieve from.
        *keys: Keys to navigate through the dictionary.
        default: Default value if key not found.

    Returns:
        Value at the nested key path or default.
    """
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data


def chunk_list(lst: list[T], chunk_size: int) -> list[list[T]]:
    """Split list into chunks.

    Args:
        lst: List to split.
        chunk_size: Size of each chunk.

    Returns:
        List of chunks.
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def retry_async(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to retry async functions.

    Args:
        max_retries: Maximum number of retries.
        delay: Initial delay between retries.
        backoff: Multiplier for delay after each retry.

    Returns:
        Decorated function with retry logic.
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}",
                        error=str(e),
                        delay=current_delay
                    )
                    if attempt < max_retries:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff

            raise last_exception

        return wrapper
    return decorator