from datetime import datetime
from uuid import UUID

import sqlalchemy
from fastapi import APIRouter, Depends, Request, Response
from fastapi_pagination import Page
from pydantic import parse_obj_as
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.cargo_insurance.schema import (
    CargoRate,
    ICreate,
    IFilter,
    IRead,
    ISearch,
    ISort,
    IUpdate,
)
from app.model import User
from app.user.service import IAuthContext, get_auth_context
from core.base.kafka import AIOWebProducer, get_producer
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

router = APIRouter(tags=["cargo_insurance"], prefix="/cargo_insurance")
# Если связь many to many то необходимо указывать целевую таблицу и связь из начальной таблицы.
mapping_filters = {}
PaginateQueryParams = PaginateQueryParams.update(
    search=ISearch,
    filter=IFilter,
    sort=ISort,
    read=IRead,
    model="CargoInsurance",
    mapping_filters=mapping_filters,
    period_mode="date",
)


@router.get(
    "/list",
    response_model=IGetResponseBase[Page[IRead]],
    response_model_exclude_none=True,
)
async def paginate(
    request: Request,
    cost: float,
    db_session: AsyncSession = Depends(get_session),
    auth_context: IAuthContext = Depends(get_auth_context),
    query_params: dict = Depends(PaginateQueryParams),
    producer: AIOWebProducer = Depends(get_producer),
):
    data = await crud.cargo_insurance.get(
        db_session,
        query_params=query_params,
        disable_joinedload=True,
    )
    data_cost = parse_obj_as(list[IRead], data.items)
    data_cost = [x.dict() | {"cost": cost} for x in data_cost]
    data.items = data_cost
    await producer.send(value="123")
    return IGetResponseBase[Page[IRead]](data=data)


@router.get("/{id}", response_model=IGetResponseBase[IRead])
async def get(
    id: UUID,
    db_session: AsyncSession = Depends(get_session),
    auth_context: IAuthContext = Depends(get_auth_context),
):
    data = await crud.cargo_insurance.get(  # todo query в параметрах
        db_session,
        id=id,
        disable_joinedload=True,
    )
    return IGetResponseBase[IRead](data=data)


@router.post("", response_model=IPostResponseBase[IRead])
async def create(
    data: list[ICreate] | ICreate,
    db_session: AsyncSession = Depends(get_session),
):
    try:
        data = await crud.cargo_insurance.create(db_session, obj_in=data)
        await db_session.commit()
        data = await crud.cargo_insurance.get(
            db_session,
            id=data.id,
            disable_joinedload=True,
        )

    except sqlalchemy.exc.IntegrityError as e:
        raise ConflictException(detail=f"error: {e}")
    return IPostResponseBase[IRead](data=data)


@router.post("/create_all", response_model=IPostResponseBase[IRead])
async def create_all(
    data: dict,
    db_session: AsyncSession = Depends(get_session),
    auth_context: IAuthContext = Depends(get_auth_context),
):
    try:
        cargo_data = []
        for date, cargo in data.items():
            cargo_rate = parse_obj_as(list[CargoRate], cargo)
            cargo_data.extend(
                [ICreate.parse_obj(x.dict() | {"date": date}) for x in cargo_rate]
            )
        data = await crud.cargo_insurance.create(
            db_session, obj_in=cargo_data, user=auth_context.user
        )
        await db_session.commit()
        data = await crud.cargo_insurance.get(
            db_session,
            id=data.id if not isinstance(data, list) else [x.id for x in data],
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
        await crud.cargo_insurance.update(
            db_session=db_session, id=id, obj_new=data, user=auth_context.user
        )
        data = await crud.cargo_insurance.get(
            db_session,
            id=id,
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
    try:
        data = await crud.cargo_insurance.remove(db_session, id=id)
    except sqlalchemy.exc.IntegrityError as e:
        raise BadRequestException(detail=f"user delete failed: {e}")
    return IDeleteResponseBase[IRead](data=data)
