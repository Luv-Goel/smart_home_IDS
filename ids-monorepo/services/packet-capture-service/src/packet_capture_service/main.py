"""Main entry point for packet capture service.

This module provides the main entry point and CLI interface.
"""

import asyncio
import signal
from typing import Optional

from ids_core.config import Settings, get_settings
from ids_core.logger import setup_logging

from packet_capture_service.service import PacketCaptureService


def create_app(settings: Optional[Settings] = None) -> PacketCaptureService:
    """Create packet capture service.

    Args:
        settings: Settings instance (optional)

    Returns:
        PacketCaptureService instance
    """
    settings = settings or get_settings()
    setup_logging()

    return PacketCaptureService(settings)


async def run_service() -> None:
    """Run the packet capture service."""
    settings = get_settings()
    service = create_app(settings)

    # Set up signal handlers
    loop = asyncio.get_event_loop()
    stop = loop.create_future()

    def signal_handler():
        if not stop.done():
            stop.set_result(None)

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await service.start()
        await stop
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(run_service())