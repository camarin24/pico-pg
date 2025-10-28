"""Handles database connection pooling for the micro-pg ORM.

This module provides a `ConnectionManager` class that abstracts the setup,
teardown, and access to the `psycopg` asynchronous connection pool.
"""

from __future__ import annotations

from psycopg_pool import AsyncConnectionPool


class ConnectionManager:
    """Manages the asynchronous database connection pool.

    This class provides a centralized way to initialize, close, and access
    the `psycopg_pool.AsyncConnectionPool`.
    """

    _pool: AsyncConnectionPool | None = None

    @classmethod
    async def initialize(cls, dsn: str, **kwargs) -> None:
        """Initializes the connection pool.

        This method should be called once at the start of the application.

        Args:
            dsn: The database connection string.
            **kwargs: Additional arguments for `psycopg_pool.AsyncConnectionPool`.
        """
        if cls._pool is None:
            cls._pool = AsyncConnectionPool(dsn, open=False, **kwargs)
            await cls._pool.open(wait=True)

    @classmethod
    async def close(cls) -> None:
        """Closes the connection pool.

        This method should be called once at the end of the application.
        """
        if cls._pool:
            await cls._pool.close()
            cls._pool = None

    @classmethod
    def get_pool(cls) -> AsyncConnectionPool:
        """Returns the connection pool.

        Returns:
            The active `AsyncConnectionPool` instance.

        Raises:
            RuntimeError: If the connection manager has not been initialized.
        """
        if cls._pool is None:
            raise RuntimeError("ConnectionManager has not been initialized.")
        return cls._pool
