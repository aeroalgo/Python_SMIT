from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.sessions.model import Sessions
from app.sessions.schema import ICreate, IUpdate
from core.base.crud import CRUDBase


class CRUD(CRUDBase[Sessions, ICreate, IUpdate]):
    async def create(self, db_session: AsyncSession, *, obj_in: ICreate) -> Sessions:
        db_obj = obj_in
        db_session.add(db_obj)
        await db_session.commit()
        await db_session.refresh(db_obj)
        return db_obj

    async def get_by_access_token(self, db_session: AsyncSession, *, access_token: str) -> Sessions:
        sessions = await db_session.execute(select(Sessions).where(Sessions.access_token == access_token))
        return sessions.first()

    async def get_by_refresh_token(self, db_session: AsyncSession, *, refresh_token: str) -> Sessions:
        sessions = await db_session.execute(select(Sessions).where(Sessions.refresh_token == refresh_token))
        return sessions.first()


sessions = CRUD(Sessions)
