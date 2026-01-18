from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg


class Database:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def connect(self, database_url: str):
        """Create connection pool."""
        self.pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
        )

    async def disconnect(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Acquire a connection from the pool."""
        if not self.pool:
            raise RuntimeError("Database not connected")
        async with self.pool.acquire() as connection:
            yield connection


db = Database()
