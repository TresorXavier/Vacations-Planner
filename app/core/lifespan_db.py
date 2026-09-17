from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import settings
from app.core.base import Base
from app.models.users import Users
from app.models.trips import Trips
from app.models.itinerary import Itineraries

engine = create_async_engine(settings.DATA_BASE_URL)
session_maker = async_sessionmaker(engine, expire_on_commit=False)


CHECKPOINTER_DB_URI = settings.DATA_BASE_URL.replace("+asyncpg", "")

checkpointer_context_manager = None  
checkpointer = None 


async def create_db_tables():
    async with engine.begin() as con:
        await con.run_sync(Base.metadata.create_all)


async def create_session():
    async with session_maker() as session:
        yield session


async def init_checkpointer():
    global checkpointer_context_manager, checkpointer
    checkpointer_context_manager = AsyncPostgresSaver.from_conn_string(CHECKPOINTER_DB_URI)
    checkpointer = await checkpointer_context_manager.__aenter__()
    await checkpointer.setup() 


async def close_checkpointer():
    if checkpointer_context_manager is not None:
        await checkpointer_context_manager.__aexit__(None, None, None)