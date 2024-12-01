from __future__ import annotations

from abc import ABC
from uuid import UUID

import sqlalchemy
from fastapi import APIRouter, Depends, Response
from fastapi_pagination import Page
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.user.service import IAuthContext, get_auth_context
from core.base.crud import CRUDBase
from core.base.schema import (
    BaseUpdate,
    IDeleteResponseBase,
    IGetResponseBase,
    IPostResponseBase,
    IPutResponseBase,
    PaginateQueryParams,
)
from core.database.session import get_session
from core.exceptions import BadRequestException
from core.utils import parse_id


class BaseApi(ABC):
    """Base class for API routers.
    Provides basic CRUD operations for API routers. (get, delete, list, create, update, report)
    Attributes:
        IRead: Schema classes.
        entity (str): Entity name.
        router (APIRouter): Entity ApiRouter.
        crud (CRUDBase): Entity CRUD class.
        mapping_filters (dict): Mapping filters for CRUD operations. Default: None.
        exclude (list): Methods to exclude from api. Default: None.
        Could be excluded: ["get", "create", "update", "delete", "paginate", "report"]
    """

    IRead: type[BaseModel] | BaseModel

    def __init__(
        self,
        IRead: type[BaseModel],
        entity: str,
        router: APIRouter,
        crud: CRUDBase,
        mapping_filters: dict | None = None,
        exclude: list[str] | None = None,
    ):
        self.entity = entity
        self.router = router
        self.crud = crud
        self.IRead = self._create_entity_scheme(IRead)
        self.mapping_filters = mapping_filters
        self.exclude = exclude or []
        self.include_router()

    def _create_entity_scheme(self, scheme: BaseModel) -> type:
        """Create entity scheme to avoid conflicts with other entities in Swagger.
        IRead -> AccountIRead, ICreate -> AccountICreate, etc.
        """
        return type(f"{self.entity.capitalize()}{scheme.__name__}", (scheme,), {})

    async def get_prefilters(self, db_session: AsyncSession, paginate_query_params: PaginateQueryParams) -> list[dict]:
        """Get prefilters for paginate."""
        return []

    async def _create(
        self,
        data: list[BaseModel] | BaseModel,
        db_session: AsyncSession,
        auth_context: IAuthContext,
    ) -> IPostResponseBase:
        """
        POST api/{version}/{entity}
        Wrapper for create method to use in router. Should be redefined in entity class.
        """
        raise NotImplementedError("_create method should be implemented in entity class or excluded.")
        # return await self.create(data, auth_context, db_session) - return in entity class

    async def _update(
        self,
        data: BaseUpdate,
        entity_id: list[UUID],
        db_session: AsyncSession,
        auth_context: IAuthContext,
    ) -> IPutResponseBase:
        """
        PATCH api/{version}/{entity}/{id}
        Wrapper for update method to use in router. Should be redefined in entity class.
        """
        raise NotImplementedError("_update method should be implemented in entity class or excluded.")
        # return await self.update(data, id, auth_context, db_session) - return in entity class

    async def _paginate(
        self,
        query_params: PaginateQueryParams,
        db_session: AsyncSession,
        auth_context: IAuthContext,
    ) -> IGetResponseBase:
        """
        GET api/{version}/{entity}/list
        Wrapper for paginate method to use in router. Should be redefined in entity class.
        """
        raise NotImplementedError("_paginate method should be implemented in entity class or excluded.")
        # return await self.paginate(db_session, auth_context) - return in entity class

    async def _report(
        self,
        query_params: dict,
        db_session: AsyncSession,
        auth_context: IAuthContext,
    ):
        """GET api/{version}/{entity}/report
        Wrapper for report method to use in router. Should be redefined in entity class."""
        raise NotImplementedError("_paginate method should be implemented in entity class or excluded.")
        # return await self.report(db_session, auth_context, query_params, s3_client) - return in entity class

    async def get(
        self,
        id: UUID,
        db_session: AsyncSession = Depends(get_session),
        auth_context: IAuthContext = Depends(get_auth_context),
    ) -> IGetResponseBase:
        """Get entity by id.
        Method for GET api/{version}/{entity}/{id}."""
        data = await self.crud.get(db_session, id=id, visibility_group=auth_context.visibility_group)
        return IGetResponseBase[self.IRead](data=data)

    async def paginate(
        self,
        query_params: PaginateQueryParams,
        db_session: AsyncSession,
        auth_context: IAuthContext,
    ) -> IGetResponseBase:
        """Get entities with pagination.
        Method for GET api/{version}/{entity}/list."""
        meta = (
            {
                "table_name": self.entity,
                "table_mapping": self.IRead.get_table_mapping(),
                "prefilters": await self.get_prefilters(db_session, query_params),
            }
            if query_params.meta
            else {}
        )
        data = await self.crud.get(
            db_session,
            mapping=self.mapping_filters,
            query_params=query_params,
            visibility_group=auth_context.visibility_group,
        )
        return IGetResponseBase[Page[self.IRead]](data=data, meta=meta)

    async def create(
        self,
        data: dict | list,
        db_session: AsyncSession,
        auth_context: IAuthContext,
    ):
        """Create entity.
        Method for POST api/{version}/{entity}."""
        data = await self.crud.create(db_session=db_session, obj_in=data, user=auth_context.user)
        return IPostResponseBase[self.IRead](data=data)

    async def update(
        self,
        data: BaseUpdate,
        entity_id: list[UUID],
        db_session: AsyncSession,
        auth_context: IAuthContext,
    ):
        """Update entity.
        Method for PATCH api/{version}/{entity}/{id}."""
        await self.crud.update(db_session=db_session, obj_new=data, id=entity_id, user=auth_context.user)
        data = await self.crud.get(db_session, id=entity_id)
        return IPutResponseBase[self.IRead](data=data)

    async def report(
        self,
        db_session: AsyncSession,
        auth_context: IAuthContext,
        query_params: dict,  # noqa
        s3_client: S3ClientWrapper,
    ) -> IGetResponseBase[ReportResponse]:
        """Generate report for entities.
        Method for GET api/{version}/{entity}/report."""
        delattr(query_params, "page")
        delattr(query_params, "size")
        data = await self.crud.get(
            db_session,
            query_params=query_params,
            visibility_group=auth_context.visibility_group,
        )
        x = Report(
            data=data,
            type_report=self.entity,
            table_mapping=self.IRead.get_table_mapping(),
            s3_client=s3_client,
            schema=self.IRead,
        )
        file = await x.generate_report()
        return Response(**file)

    async def delete(
        self,
        id: UUID | list[UUID] = Depends(parse_id),
        db_session: AsyncSession = Depends(get_session),
        auth_context: IAuthContext = Depends(get_auth_context),
    ) -> IDeleteResponseBase:
        """Delete entity by id.
        Method for DELETE api/{version}/{entity}/{id}."""
        try:
            await self.crud.remove(db_session, id=id)
        except sqlalchemy.exc.IntegrityError as e:
            raise BadRequestException(detail=f"{self.entity} {id=} delete failed: {e}")
        return IDeleteResponseBase()

    def include_router(self):
        """Add routes of BaseAPI to router excluding methods from self.exclude."""

        if "create" not in self.exclude:
            self.router.add_api_route(
                "",
                endpoint=self._create,
                methods=["POST"],
                response_model=IPostResponseBase[self.IRead],
            )
        if "update" not in self.exclude:
            self.router.add_api_route(
                "/{id}",
                self._update,
                methods=["PATCH"],
                response_model=IPutResponseBase[self.IRead],
            )
        if "paginate" not in self.exclude:
            self.router.add_api_route(
                "/list",
                self._paginate,
                methods=["GET"],
                response_model=IGetResponseBase[Page[self.IRead]],
                response_model_exclude_none=True,
            )
        if "get" not in self.exclude:
            self.router.add_api_route(
                "/{id}",
                self.get,
                methods=["GET"],
                response_model=IGetResponseBase[self.IRead],
            )
        if "delete" not in self.exclude:
            self.router.add_api_route(
                "/{id}",
                self.delete,
                methods=["DELETE"],
                response_model=IDeleteResponseBase,
            )
        return self.router
