from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from core.base.schema import BaseFilter, BaseSort, BaseUpdate, EmptyBaseSchema


__all__ = (
    "ICreate",
    "IRead",
    "IUpdate",
    "IFilter",
    "ISort",
    "ISearch",
)


class ICreate(BaseModel):
    __model_name__ = "Sessions"


class IUpdate(BaseUpdate):
    __model_name__ = "Sessions"


class IRead(EmptyBaseSchema):
    __model_name__ = "Sessions"

    id: Optional[UUID]
    cookie: Optional[str]
    access_token: Optional[str]
    refresh_token: Optional[str]
    token_type: Optional[str]
    expires_at: Optional[int]
    user_id: Optional[UUID]


class IFilter(BaseFilter):
    __model_name__ = "Sessions"

    # для совместимости, todo удалить
    user_id: Optional[UUID | list[UUID | None]]


class ISort(BaseSort):
    __model_name__ = "Sessions"


class ISearch(BaseFilter):
    __model_name__ = "Sessions"
