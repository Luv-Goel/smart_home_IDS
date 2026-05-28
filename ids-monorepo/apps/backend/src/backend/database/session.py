"""Database session management for Smart Home IDS.

This module provides async session management and utilities.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.database.config import DatabaseConfig, get_database_config


# Default database config
db_config = get_database_config()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions.

    Yields:
        Async database session
    """
    async with db_config.session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


class AsyncSessionLocal:
    """Async session local context manager."""

    def __init__(self):
        """Initialize session local."""
        self.session_factory = db_config.session_factory

    async def __aenter__(self) -> AsyncSession:
        """Enter async context.

        Returns:
            Async session
        """
        self.session = self.session_factory()
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        await self.session.close()