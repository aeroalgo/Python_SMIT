from uuid import UUID

import sqlalchemy
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.sessions.schema import IFilter, IRead, ISearch, ISort
from app.user.service import IAuthContext, get_auth_context
from core.base.schema import (
    IDeleteResponseBase,
    IGetResponseBase,
    PaginateQueryParams,
)
from core.database.session import get_session
from core.exceptions import BadRequestException
from fastapi_pagination import Page


entity = "sessions"
router = APIRouter(tags=["sessions"], prefix="/sessions")
PaginateQueryParams = PaginateQueryParams.update(
    search=ISearch, filter=IFilter, sort=ISort, read=IRead, model="Sessions"
)


@router.get("/list", response_model=IGetResponseBase[Page[IRead]], response_model_exclude_none=True)
async def paginate(
    db_session: AsyncSession = Depends(get_session),
    auth_context: IAuthContext = Depends(get_auth_context),
    query_params: dict = Depends(PaginateQueryParams),
):
    data = await crud.sessions.get(
        db_session,
        query_params=query_params,
    )
    return IGetResponseBase[Page[IRead]](data=data, meta={})


@router.delete("/{id}", response_model=IDeleteResponseBase[IRead])
async def remove_session(
    id: UUID,
    db_session: AsyncSession = Depends(get_session),
    auth_context: IAuthContext = Depends(get_auth_context),
):
    try:
        await crud.sessions.remove(db_session, id=id)
    except sqlalchemy.exc.IntegrityError as e:
        raise BadRequestException(detail=f"delete failed: {e}")
    return IDeleteResponseBase()
