import os
from datetime import timedelta
from enum import Enum
from typing import Any, Optional, Tuple
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_sso.sso.base import SSOBase
from fastapi_sso.sso.google import GoogleSSO
from pydantic.networks import AnyHttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import URL as URL

from app import crud
from app.auth.schema import IPassword, RefreshToken, Token
from app.model import User
from app.sessions.model import Sessions
from app.user.schema import IAuthMeta, ICreate
from app.user.service import IAuthContext, get_auth_context, reusable_oauth2
from core.base.schema import IGetResponseBase, IPostResponseBase
from core.database.session import get_session
from core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from core.logger import logger
from core.security import (
    create_cookie,
    create_jwt_token,
    create_password,
    get_password_hash,
    verify_jwt_token,
)
from core.settings import settings

router = APIRouter(tags=["auth"], prefix="/auth")


class SSOProvider(str, Enum):
    keycloak = "keycloak"
    google = "google"


def create_token_and_session(
    user, request: Request, response: Response
) -> Tuple[Token, Sessions, IAuthMeta]:

    logger.debug("auth: token creation started")

    access_token_expires = timedelta(minutes=10000)
    refresh_token_expires = timedelta(minutes=10000)

    access_token, expires_at = create_jwt_token(
        {
            "user_id": str(user.id),
            "email": user.email,
        },
        expires_delta=access_token_expires,
        token_type="access",
    )

    refresh_token, _ = create_jwt_token(
        {"user_id": str(user.id)},
        expires_delta=refresh_token_expires,
        token_type="refresh",
    )

    cookie = request.cookies.get("auth")
    if not cookie:
        cookie = create_cookie()
        response.set_cookie(key="auth", value=cookie, httponly=True, secure=True)

    data = Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        expires_at=expires_at,
    )

    session = Sessions(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        expires_at=expires_at,
        cookie=cookie,
    )

    meta = IAuthMeta.parse_obj(user.__dict__)
    logger.debug("auth: token creation completed")
    return data, session, meta


async def refresh_user_sessions(
    user: User, request: Request, db_session: AsyncSession, session: Sessions
):
    if user.sessions:
        for i in user.sessions:
            if i.cookie == request.cookies.get("auth"):
                await crud.sessions.remove(db_session, id=i.id)
        if len(user.sessions) >= 3:
            oldest_session = sorted(user.sessions, key=lambda x: x.created_at)[0]
            await crud.sessions.remove(db_session, id=oldest_session.id)
    await crud.sessions.create(db_session, obj_in=session)


@router.post(
    "/basic",
    response_model=IPostResponseBase[Token],
    status_code=201,
    responses={
        409: {
            "content": {
                "application/json": {"example": {"detail": "User is disabled"}}
            },
            "description": "Additional information about the error",
        }
    },
)
async def basic(
    response: Response,
    request: Request,
    db_session: AsyncSession = Depends(get_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
    # meta_data: IMetaGeneral = Depends(get_general_meta) # TODO return available roles
) -> Any:
    """
    Basic login for test users only. Disabled for rest of the users.
    """
    user = await crud.user.authenticate(
        db_session, email=form_data.username, password=form_data.password
    )
    data, session, meta = create_token_and_session(user, request, response)
    await refresh_user_sessions(user, request, db_session, session)
    return IPostResponseBase[Token](meta=meta, data=data, message="Login correctly")


@router.get(
    "/logout",
    response_model=IGetResponseBase,
    responses={
        401: {
            "content": {
                "application/json": {
                    "example": {"detail": "The session does not exist"}
                }
            },
            "description": "If user can't be authenticated",
        },
        403: {
            "content": {
                "application/json": {
                    "example": {"detail": "User does not have permission"}
                }
            },
            "description": "If user authenticated but not authorized",
        },
        404: {
            "content": {"application/json": {"example": {"detail": "Not found"}}},
            "description": "Not found",
        },
        409: {
            "content": {"application/json": {"example": {"detail": "Conflict"}}},
            "description": "Conflict",
        },
    },
)
async def logout(
    request: Request,
    db_session: AsyncSession = Depends(get_session),
    auth_context: IAuthContext = Depends(get_auth_context),
    access_token: str = Depends(reusable_oauth2),
    all_devices: bool = False,  # Для кнопки на фронте "выйти на всех устройствах"
):
    session_ids = []
    if auth_context.user.sessions:
        if all_devices:
            session_ids = [session.id for session in auth_context.user.sessions]
        else:
            for i in auth_context.user.sessions:
                if (
                    i.cookie == request.cookies.get("auth")
                    or i.access_token == access_token
                ):
                    session_ids.append(i.id)
        await crud.sessions.remove(db_session, id=session_ids)
    return IGetResponseBase(data={})


@router.get(
    "/{provider}/callback",
    response_model=IGetResponseBase[Token],
    status_code=200,
    responses={
        400: {
            "content": {"application/json": {"example": {"detail": "Bad request"}}},
            "description": "Bad request",
        },
        404: {
            "content": {"application/json": {"example": {"detail": "Not found"}}},
            "description": "Not found",
        },
        409: {
            "content": {"application/json": {"example": {"detail": "Conflict"}}},
            "description": "Conflict",
        },
    },
)
@router.post(
    "/refresh-token",
    response_model=IPostResponseBase[Token],
    response_model_exclude_none=False,
    status_code=201,
    responses={
        401: {
            "content": {
                "application/json": {
                    "example": {"detail": "The session does not exist"}
                }
            },
            "description": "If user can't be authenticated",
        },
        404: {
            "content": {"application/json": {"example": {"detail": "Not found"}}},
            "description": "Not found",
        },
        409: {
            "content": {"application/json": {"example": {"detail": "Conflict"}}},
            "description": "Conflict",
        },
    },
)
async def refresh_token(
    request: Request,
    response: Response,
    body: RefreshToken = Body(...),
    db_session: AsyncSession = Depends(get_session),
) -> Any:
    """
    Get Refresh token
    """
    payload = await verify_jwt_token(
        token=body.refresh_token, token_type="refresh", db_session=db_session, crud=crud
    )
    try:
        user = await crud.user.get_user_session(db_session, id=payload["user_id"])
    except Exception as e:
        raise ConflictException(detail=f"database error: {e}")
    if not user:
        raise NotFoundException(detail="User not found")
    elif not user.is_active:
        raise ConflictException(detail="User is disabled")
    if not user.sessions:
        raise UnauthorizedException(detail="The session does not exist")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token, expires_at = create_jwt_token(
        {
            "user_id": str(user.id),
            "email": user.email,
            "roles": {str(i.id): i.title for i in user.roles},
            "teams": [str(i.id) for i in user.teams],
            "visibility_group": (
                user.visibility_group.prefix if user.visibility_group else None
            ),
        },
        expires_delta=access_token_expires,
        token_type="access",
    )
    data = Token(
        access_token=access_token,
        token_type="bearer",
        expires_at=expires_at,
        refresh_token=body.refresh_token,
    )
    meta = IAuthMeta.parse_obj(user.__dict__)
    cookie = request.cookies.get("auth")
    for s in user.sessions:
        if s.refresh_token == body.refresh_token:
            if not cookie:
                if s.cookie:
                    cookie = s.cookie
                    response.set_cookie(
                        key="auth", value=cookie, httponly=True, secure=True
                    )
                else:
                    cookie = create_cookie()
                    response.set_cookie(
                        key="auth", value=cookie, httponly=True, secure=True
                    )
            await crud.sessions.update(
                db_session,
                id=[s.id],
                obj_new={
                    "access_token": access_token,
                    "expires_at": expires_at,
                    "cookie": cookie,
                },
            )
            return IPostResponseBase[Token](
                meta=meta, data=data, message="Access token generated correctly"
            )
    raise UnauthorizedException(detail="The session does not exist")


@router.get(
    "/basic/reset-password/{id}",
    response_model=IGetResponseBase[IPassword],
    status_code=201,
    responses={
        409: {
            "content": {
                "application/json": {"example": {"detail": "User is disabled"}}
            },
            "description": "Additional information about the error",
        }
    },
)
async def basic_reset_password(
    id: UUID,
    db_session: AsyncSession = Depends(get_session),
    auth_context: IAuthContext = Depends(get_auth_context),
) -> Any:
    """
    Basic password reset.
    """
    password = create_password()
    hashed_password = get_password_hash(password)
    meta = {}
    data = {"password": password}
    try:
        await crud.user.update(
            db_session, obj_new={"hashed_password": hashed_password}, id=[id]
        )
    except Exception as e:
        raise ConflictException(detail=f"database error: {e}")
    return IGetResponseBase[IPassword](meta=meta, data=data, message="New password")
