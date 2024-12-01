from typing import Any, Optional, Union
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    EmailStr,
    StrictBool,
    StrictStr,
    root_validator,
    validator,
)

from app.sessions.schema import IRead as IReadSessions
from core.base.schema import (
    BaseFilter,
    BaseMeta,
    BaseSchema,
    BaseSort,
    BaseUpdate,
    ImageUrl,
)
from core.security import create_password, get_password_hash

__all__ = (
    "ICreate",
    "IRead",
    "IReadUserWithSessions",
    "IUpdate",
    "IFilter",
    "IAuthMeta",
    "ISort",
    "ISearch",
)


class IFilter(BaseFilter):
    __model_name__ = "User"

    visibility_group_id: Optional[UUID | list[UUID | None]]
    first_name: Optional[StrictStr]
    last_name: Optional[StrictStr]
    full_name: Optional[StrictStr]
    email: Optional[EmailStr]
    is_active: Optional[StrictBool | list[StrictBool | None]]
    roles: Optional[Union[str, list[str | None]]]


class ICreate(BaseModel):
    __model_name__ = "User"
    first_name: str
    last_name: str
    password: str
    full_name: Optional[str]
    email: EmailStr
    is_active: Optional[bool]
    picture: Optional[AnyHttpUrl]

    @validator("email")
    def str_attr_must_be_lower(cls, v):
        return v.lower().strip()

    @root_validator
    def create_password(cls, values):
        # values["password"] = create_password()
        values["allow_basic_login"] = True
        return values

    @root_validator
    def create_hashed_password(cls, values):
        values["hashed_password"] = get_password_hash(values["password"])
        del values["password"]
        return values

    @root_validator
    def create_full_name(cls, values):
        if "last_name" not in values:
            values["last_name"] = ""
        if not values["full_name"]:
            values["full_name"] = (
                f"{values['first_name']} {values['last_name']}".strip()
            )
        return values

    @root_validator
    def activate_user(cls, values):
        if "is_active" not in values:
            values["is_active"] = False
        return values

    @root_validator
    def delete_none(cls, values):
        for key in list(values.keys()):
            if values[key] is None:
                del values[key]
        return values


class IAuthMeta(BaseMeta):
    id: UUID
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: Optional[str]
    email: Optional[EmailStr]
    roles: Optional[Any]
    teams: Optional[list[Any]]
    picture: Optional[AnyHttpUrl] = None
    visibility_group: Optional[Any]
    ui_settings: Optional[dict]
    visibility_group__prefix: Optional[str]

    @root_validator
    def get_relation_data(cls, values):
        if values.get("visibility_group"):
            values["visibility_group__prefix"] = values.get("visibility_group").prefix
            del values["visibility_group"]
        if values.get("roles"):
            values["roles__title"] = [x.title for x in values["roles"]]
            del values["roles"]
        return values


class IRead(BaseSchema):
    __model_name__ = "User"
    picture: Optional[AnyHttpUrl] = None
    roles: Optional[list[Any]]
    teams: Optional[list[Any]]
    visibility_group: Optional[Any]
    is_active: Optional[bool]
    email: Optional[EmailStr]
    visibility_group__prefix: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: Optional[str]
    ui_settings: Optional[dict]

    @root_validator
    def remove_sensitive_data(cls, values):
        if "hashed_password" in values:
            del values["hashed_password"]
        return values

    @root_validator
    def get_relation_data(cls, values):
        if values.get("visibility_group"):
            values["visibility_group__prefix"] = values.get("visibility_group").prefix
            del values["visibility_group"]
        if values.get("roles"):
            values["roles__title"] = [x.title for x in values["roles"]]
            del values["roles"]
        if values.get("teams"):
            values["teams__title"] = [x.title for x in values["teams"]]
            del values["teams"]
        return values


class IReadUserWithSessions(IRead):
    sessions: Optional[list[IReadSessions]]


class IUpdate(BaseUpdate):
    __model_name__ = "User"

    visibility_group_id: Optional[UUID]
    role_id: Optional[list[UUID] | UUID]
    team_id: Optional[list[UUID] | UUID]
    phone: Optional[str]
    country: Optional[str]
    city: Optional[str]
    title: Optional[str]
    email: Optional[EmailStr]
    region: Optional[list]
    is_active: Optional[bool]
    is_staff: Optional[bool]
    is_superuser: Optional[bool]
    allow_basic_login: Optional[bool]
    country_code: Optional[str]
    phone_confirmation_code: Optional[str]
    first_name: Optional[str]
    ui_settings: Optional[dict]


class IUpdateMe(BaseUpdate):
    __model_name__ = "User"

    ui_settings: Optional[dict]


class ISort(BaseSort):
    __model_name__ = "User"

    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[EmailStr]
    visibility_group__prefix: Optional[str]


class ISearch(BaseFilter):
    __model_name__ = "User"
