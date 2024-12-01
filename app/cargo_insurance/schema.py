from datetime import date, datetime
from enum import Enum
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel, root_validator, validator
from pydantic.datetime_parse import parse_datetime

from core.base.schema import BaseFilter, BaseSchema, BaseSort, BaseUpdate


class ICreate(BaseModel):
    __model_name__ = "CargoInsurance"

    date: Optional[date]
    cargo_type: Optional[str]
    rate: Optional[float]


class CargoRate(BaseModel):
    cargo_type: Optional[str]
    rate: Optional[float]


class IRead(BaseSchema):
    __model_name__ = "CargoInsurance"
    cost: Optional[float]
    date: Optional[datetime]
    cargo_type: Optional[str]
    rate: Optional[float]
    full_cost: Optional[float]

    @root_validator
    def calc_full_cost(cls, values):
        if values.get("cost"):
            values["full_cost"] = values["cost"] * values["rate"]
        return values


class IUpdate(BaseUpdate):
    __model_name__ = "CargoInsurance"

    price_action: Optional[int]
    stock: Optional[int]


class IFilter(BaseFilter):
    __model_name__ = "CargoInsurance"
    date: Union[datetime]
    cargo_type: Optional[str | list[str | None]]
    rate: Optional[float | list[float | None]]


class ISort(BaseSort):
    __model_name__ = "CargoInsurance"

    date: Optional[datetime]
    cargo_type: Optional[str]
    rate: Optional[float]


class ISearch(BaseFilter):
    __model_name__ = "CargoInsurance"

    date: Optional[datetime]
    cargo_type: Optional[str]
    rate: Optional[float]
