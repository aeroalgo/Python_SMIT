import asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session
from sqlalchemy.orm import sessionmaker

from core.database.database import async_engine


__all__ = "get_session"


async_session_factory = sessionmaker(
    bind=async_engine, expire_on_commit=False, class_=AsyncSession, autocommit=False, autoflush=False
)

# passing a lambda function to async_scoped_session that returns the ID of the current asyncio task as the session scope.
# This ensures that each session is associated with a unique task and gets its own connection.
async_session_factory = async_scoped_session(async_session_factory, scopefunc=lambda: id(asyncio.current_task()))


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()