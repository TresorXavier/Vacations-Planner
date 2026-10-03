# app/core/lifespan_db.py
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import settings
from app.core.base import Base
from app.models.users import Users          # imported so the tables are registered
from app.models.trips import Trips
from app.models.itinerary import Itineraries


class Database:
    """Owns the engine, the sessions and the LangGraph checkpointer."""

    def __init__(self, url: str):
        self.engine: AsyncEngine = create_async_engine(url)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)
        self._checkpointer_uri = url.replace("+asyncpg", "")
        self._checkpointer_contmanager = None
        self.checkpointer: AsyncPostgresSaver | None = None

    async def startup(self) -> None:
        async with self.engine.begin() as con:
            await con.run_sync(Base.metadata.create_all)

        self._checkpointer_contmanager = AsyncPostgresSaver.from_conn_string(self._checkpointer_uri)
        self.checkpointer = await self._checkpointer_contmanager.__aenter__()
        await self.checkpointer.setup()

    async def shutdown(self) -> None:
        if self._checkpointer_contmanager is not None:
            await self._checkpointer_contmanager.__aexit__(None, None, None)
        await self.engine.dispose()


database = Database(settings.DATA_BASE_URL)


async def create_session():
    async with database.session_maker() as session:
        yield session