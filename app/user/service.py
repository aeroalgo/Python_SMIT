from dataclasses import dataclass
from typing import NamedTuple, Optional
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.user.model import User
from core.database.session import get_session
from core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from core.logger import logger
from core.security import verify_jwt_token
from core.settings import settings

__all__ = (
    "IAuthContext",
    "reusable_oauth2",
)

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=settings.token_url)


@dataclass
class IAuthContext:
    user: User = None
    payload: dict = None


async def get_auth_context(
    request: Request,
    db_session: AsyncSession = Depends(get_session),
    access_token: str = Depends(reusable_oauth2),
) -> IAuthContext:
    # get entity name from request url /api/v1/entity/list
    entity = request.url.path.split("/")[3]
    data = IAuthContext()
    data.payload = await verify_jwt_token(
        token=access_token, token_type="access", db_session=db_session, crud=crud
    )
    data.user = await crud.user.get_user_session(db_session, id=data.payload["user_id"])
    if not data.user:
        raise NotFoundException(detail="auth: user not found")
    if not data.user.sessions:
        raise UnauthorizedException(detail="auth: user has no active sessions")
    if not data.user.is_active:
        raise ConflictException(detail="auth: user is not active")
    if data.user.is_superuser:
        return data
    logger.debug(f"get_auth_context user: {data.user}")
    logger.debug(f"get_auth_context payload: {data.payload}")
    return data
