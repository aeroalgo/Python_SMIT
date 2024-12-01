from datetime import datetime
from uuid import UUID

import sqlalchemy
from fastapi import APIRouter, Depends, Response
from fastapi_pagination import Page
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.model import User
from app.user.schema import (
    ICreate,
    IFilter,
    IRead,
    IReadUserWithSessions,
    ISearch,
    ISort,
    IUpdate,
    IUpdateMe,
)
from app.user.service import IAuthContext, get_auth_context
from core.base.schema import (
    IDeleteResponseBase,
    IGetResponseBase,
    IPostResponseBase,
    IPutResponseBase,
    PaginateQueryParams,
)
from core.database.session import get_session
from core.exceptions import BadRequestException, ConflictException
from core.logger import logger
from core.utils import parse_id

router = APIRouter(tags=["user"], prefix="/user")
# Если связь many to many то необходимо указывать целевую таблицу и связь из начальной таблицы.
mapping_filters = {}
PaginateQueryParams = PaginateQueryParams.update(
    search=ISearch,
    filter=IFilter,
    sort=ISort,
    read=IRead,
    model="User",
    mapping_filters=mapping_filters,
)


@router.get(
    "/list",
    response_model=IGetResponseBase[Page[IRead]],
    response_model_exclude_none=True,
)
async def paginate(
    db_session: AsyncSession = Depends(get_session),
    auth_context: IAuthContext = Depends(get_auth_context),
    query_params: dict = Depends(PaginateQueryParams),
):
    data = await crud.user.get(
        db_session,
        query_params=query_params,
        disable_joinedload=True,
    )
    return IGetResponseBase[Page[IRead]](data=data)


@router.get("/{id}", response_model=IGetResponseBase[IReadUserWithSessions])
async def get(
    id: UUID,
    db_session: AsyncSession = Depends(get_session),
    auth_context: IAuthContext = Depends(get_auth_context),
):
    data = await crud.user.get(  # todo query в параметрах
        db_session,
        id=id,
        disable_joinedload=True,
    )
    return IGetResponseBase[IReadUserWithSessions](data=data)


@router.post("", response_model=IPostResponseBase[IRead])
async def create(
    data: list[ICreate] | ICreate,
    db_session: AsyncSession = Depends(get_session),
):
    try:
        data = await crud.user.create(db_session, obj_in=data)
        await db_session.commit()
        data = await crud.user.get(
            db_session,
            id=data.id,
            disable_joinedload=True,
        )

    except sqlalchemy.exc.IntegrityError as e:
        raise ConflictException(detail=f"error: {e}")
    return IPostResponseBase[IRead](data=data)


@router.patch("/{id}", response_model=IPutResponseBase[IRead])
async def update(
    data: IUpdate,
    db_session: AsyncSession = Depends(get_session),
    id: list[UUID] = Depends(parse_id),
    auth_context: IAuthContext = Depends(get_auth_context),
):

    try:
        await crud.user.update(
            db_session=db_session, id=id, obj_new=data, user=auth_context.user
        )
        data = await crud.user.get(
            db_session,
            id=id,
            include_model=["visibility_group", "roles", "teams"],
            disable_joinedload=True,
        )
    except sqlalchemy.exc.IntegrityError as e:
        raise BadRequestException(detail=f"error: {e}")
    return IPutResponseBase[IRead](data=data)


@router.delete("/{id}", response_model=IDeleteResponseBase[IRead])
async def delete(
    id: UUID | list[UUID] = Depends(parse_id),
    db_session: AsyncSession = Depends(get_session),
    auth_context: IAuthContext = Depends(get_auth_context),
):
    if isinstance(id, UUID):
        id = [id]
    if auth_context.user.id in id:
        raise BadRequestException(detail="You cannot delete yourself")
    try:
        data = await crud.user.remove(db_session, id=id)
    except sqlalchemy.exc.IntegrityError as e:
        raise BadRequestException(detail=f"user delete failed: {e}")
    return IDeleteResponseBase[IRead](data=data)


@router.get(
    "", response_model_exclude_none=False, response_model=IGetResponseBase[IRead]
)
async def get_me(
    auth_context: IAuthContext = Depends(get_auth_context),
):
    return IGetResponseBase[IRead](data=auth_context.user)


@router.patch("", response_model=IGetResponseBase[IRead])
async def update_me(
    data: IUpdateMe,
    db_session: AsyncSession = Depends(get_session),
    auth_context: IAuthContext = Depends(get_auth_context),
):
    try:
        await crud.user.update(db_session, id=[auth_context.user.id], obj_new=data)
    except sqlalchemy.exc.IntegrityError as e:
        raise BadRequestException(detail=f"user update failed: {e}")
    return IPutResponseBase()


@router.delete("", response_model=IGetResponseBase)
async def delete_me(
    db_session: AsyncSession = Depends(get_session),
    auth_context: IAuthContext = Depends(get_auth_context),
):
    try:
        await crud.user.remove(db_session, id=auth_context.user.id)
    except sqlalchemy.exc.IntegrityError as e:
        raise BadRequestException(detail=f"user delete failed: {e}")
    return IDeleteResponseBase()
