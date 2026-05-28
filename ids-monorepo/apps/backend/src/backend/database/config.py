"""Database configuration for Smart Home IDS.

This module provides database configuration and connection utilities.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker, sessionmaker
from sqlalchemy.pool import StaticPool, AsyncAdaptedQueuePool

from ids_core.config import Settings


class DatabaseConfig:
    """Database configuration."""

    def __init__(self, settings: Settings):
        """Initialize database configuration.

        Args:
            settings: Settings instance
        """
        self.settings = settings
        self.engine = self._create_engine()
        self.session_factory = self._create_session_factory()

    def _create_engine(self) -> AsyncEngine:
        """Create async database engine.

        Returns:
            Async database engine
        """
        connect_args = {}

        # SQLite configuration for development/testing
        if "sqlite" in self.settings.database_url:
            connect_args = {"check_same_thread": False}

        return create_async_engine(
            self.settings.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=self.settings.database_pool_size,
            max_overflow=self.settings.database_max_overflow,
            poolclass=StaticPool if "sqlite" in self.settings.database_url else AsyncAdaptedQueuePool,
            connect_args=connect_args,
        )

    def _create_session_factory(self):
        """Create async session factory.

        Returns:
            Async session factory
        """
        return sessionmaker(
            bind=self.engine,
            class_="AsyncSession",  # type: ignore
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    async def get_session(self):
        """Get a new async session.

        Yields:
            Async session
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self) -> None:
        """Close database engine."""
        await self.engine.dispose()


def get_database_config() -> DatabaseConfig:
    """Get database configuration singleton.

    Returns:
        DatabaseConfig instance
    """
    from ids_core.config import get_settings

    return DatabaseConfig(get_settings())