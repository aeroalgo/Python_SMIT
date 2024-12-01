import asyncio

from sqlalchemy import MetaData, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool, QueuePool  # noqa

from core.exceptions import ApplicationException
from core.logger import logger
from core.settings import settings

Base = declarative_base()
metadata = MetaData()

__all__ = (
    "async_engine",
    "init_database",
    "get_engine_url",
    "job_async_engine",
)

print(settings.PSQL_HOST)


def get_engine_url():
    return make_url(settings.PSQL_ASYNC_URL)


def get_pool():
    return NullPool


async_engine = create_async_engine(
    url=get_engine_url(),
    echo=False,
    future=True,
    poolclass=get_pool(),
)


job_async_engine = create_async_engine(
    url=get_engine_url(),
    echo=False,
    pool_size=50,
    max_overflow=10,
    poolclass=AsyncAdaptedQueuePool,
)


async def db_test_connection(async_engine):
    logger.debug("database: connection test")
    for i in range(3):
        try:
            async with async_engine.begin() as conn:
                await conn.execute(select(1))
            logger.debug("database: connection success")
            break
        except Exception as e:
            logger.error(f"database: attempt {i} connection failed; reason: {e}")
            await asyncio.sleep(1)
    else:
        logger.error("database: connection failed")
        raise ApplicationException


async def init_database():
    await db_test_connection(async_engine)
    # logger.info("database: initialize")
    # async with async_engine.begin() as conn:
    # await conn.run_sync(Base.metadata.drop_all)
    # await conn.run_sync(Base.metadata.create_all)


# Here, we're using QueuePool as the connection pool class,
# which manages a queue of connections to the database. When you execute a query,
# it will automatically take a connection from the pool, execute the query,
# and return the connection to the pool. This helps ensure that only one operation
# is executed on a given connection at a time, which should help avoid the error you're seeing.
