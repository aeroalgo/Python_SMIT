from typing import Optional
from uuid import UUID

from pydantic.networks import EmailStr
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.user.model import User
from app.user.schema import ICreate, IUpdate
from core.base.crud import CRUDBase
from core.exceptions import BadRequestException, ConflictException
from core.security import verify_password


__all__ = ("user",)


class CRUD(CRUDBase[User, ICreate, IUpdate]):
    async def get_user_session(self, db_session: AsyncSession, *, id: UUID) -> Optional[User]:
        users = await db_session.execute(
            select(User)
            .where(User.id == id)
            .options(
                selectinload(User.sessions)
            )
        )
        return users.scalars().one_or_none()

    async def get_by_email(self, db_session: AsyncSession, *, email: str) -> Optional[User]:
        user = await db_session.execute(
            select(User)
            .where(User.email == email)
            .options(
                selectinload(User.sessions)
            )
        )
        user = user.scalars().one_or_none()
        return user

    async def authenticate(self, db_session: AsyncSession, *, email: EmailStr, password: str) -> Optional[User]:
        try:
            user = await self.get_by_email(db_session, email=email)
        except SQLAlchemyError as e:
            raise ConflictException(detail=f"Database error: {e}")
        if not user:
            raise BadRequestException(detail="Incorrect email or password")
        if not user.is_active:
            raise ConflictException(detail="User is disabled")
        if not user.allow_basic_login:
            raise ConflictException(detail="Basic login is disabled for this user")
        if not await verify_password(password, user.hashed_password):
            raise BadRequestException(detail="Incorrect email or password")
        return user


user = CRUD(User)
