import json
from datetime import datetime, timezone
from typing import Any, Dict, Generic, KeysView, Optional, TypeVar
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import Query
from pydantic import BaseModel, Json, root_validator, validator
from pydantic.generics import GenericModel

import app.model as models
from core.exceptions import ValidationException
from core.sdui import ColumnAnnotation
from core.settings import settings
from core.utils import (
    empty_str_to_none,
    format_key,
    get_class_properties,
    validate_field_external,
)

__all__ = (
    "IBaseUser",
    "BaseFilter",
    "BaseMeta",
    "ImageUrl",
    "IGetResponseBase",
    "IPostResponseBase",
    "IPutResponseBase",
    "IDeleteResponseBase",
    "FloatToInt",
    "RoundedFloat2DP",
    "RoundedFloat2DPWithPercentage",
    "RoundedFloat2DPWithRUB",
    "IntWithPercentage",
    "ImageOptimizedUrl",
    "Country",
    "BaseSchema",
    "BaseUpdate",
    "EmptyBaseSchema",
    "PaginateQueryParams",
    "BaseSort",
    "ReportResponse",
    "IPostResponseBase",
    "DateTimeMSK",
)


class EmptyBaseSchema(BaseModel):
    base_fields: dict = {}

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True

    @root_validator
    def format_datetime(cls, values):
        if isinstance(values.get("created_at"), datetime):
            values["created_at"] = values["created_at"].replace(microsecond=0)
        if isinstance(values.get("updated_at"), datetime):
            values["updated_at"] = values["updated_at"].replace(microsecond=0)
        return values

    class Meta:
        log_fields: list[str] = []


class ModelMetaOptions:
    def __init__(self, options=None):
        self.fields = getattr(options, "fields", {})


class BaseUUIDMeta(type(BaseModel)):  # type: ignore[misc]

    def __new__(
        cls,
        name: str,
        bases,
        attrs: Dict[str, Any],
        **kwargs: Any,
    ):
        new_class = super().__new__(cls, name, bases, attrs, **kwargs)

        # Кажется, что нет моделей без Meta свойства где прописан метакласс.
        # todo попробовать убрать ModelMetaOptions после окончания рефакторинга
        opts = new_class._meta = ModelMetaOptions(getattr(new_class, "Meta", None))
        attrs = ColumnAnnotation.__init__.__annotations__.keys()

        if opts.fields:
            for key, value in cls.base_fields.items():
                if key not in opts.fields:
                    opts.fields[key] = value

        field_keys = opts.fields.values()
        for field in field_keys:
            for key in field.keys():
                if key not in attrs:
                    raise ValueError(f"The key {key} you entered is not valid.")
        new_class.Meta.fields = opts.fields
        return new_class


class BaseSchema(EmptyBaseSchema, metaclass=BaseUUIDMeta):

    id: UUID
    updated_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_by: Optional[UUID]
    created_by: Optional[UUID]
    description: Optional[str]
    changelog: Optional[Any]


class BaseJSONSchema(BaseModel):
    def dict(self):
        return self.__root__


class DigitFilter(BaseJSONSchema):
    # todo мб лучше не разделять фильтры на числовые, а использовать аннотацию в ifilter, например так будут работать date >= date
    __root__: Json[
        Dict[str, int | float]
    ]  # todo мб лучше через typeVar, если будет время


class StringFilter(BaseJSONSchema):
    # todo не потерять конвертер null в None
    __root__: Json[
        Dict[str, list[str | None]]
    ]  # todo мб лучше через typeVar, если будет время


class StringSearch(BaseJSONSchema):
    # todo тут родильский метод dict() будет возращать list. Лучше переименовать в from_json или что-то такое
    __root__: Json[list[str]]


class StringSort(BaseJSONSchema):
    # json для единообразия
    __root__: Json[str]
    # todo возможно проще с фронта передавать список из одной строки.
    #  Будет проще мультисортировку добавить


class PeriodFilter(BaseJSONSchema):
    # json для единообразия
    __root__: str
    # todo валидатор под "date:date" строку

    @validator("__root__")
    def validator_search(cls, value: str):
        # todo потестить
        start, end = map(
            lambda x: datetime.strptime(x.strip(), "%Y-%m-%d").date(), value.split(":")
        )
        if end < start:
            raise ValidationException(
                detail="Can't process period value: end date must be greater or equal to start date"
            )
        return start, end


class PaginateQueryParams(BaseModel):
    meta: bool = Query(False)  # на первом этапе без меты в тестах
    page: int = Query(1, ge=1)
    size: int = Query(50, ge=1)
    search: str = Query(None)
    period: str = Query(None)
    scope: str = Query(None)
    ascending: str = Query(None)
    descending: str = Query(None)
    gt: str = Query(None)
    lt: str = Query(None)
    eq: str = Query(None)
    column: str = Query(None)  # потом filters планируется переименовать в column
    filters: str = Query(None)

    class Config:
        read = None  # for scope
        sort = None
        search = None
        filter = None  # ["JoinedModel__column", "Model_column"]
        model = None
        mapping_filters = None
        period_mode = None

    # todo подумать как райзить ошибки

    # todo обработчик null, None, "" возможно вложенных в лист.
    #   в общем работает, нужно поискать корнер кейсы
    def __str__(self):
        return self.json()

    def __call__(
        self,
        read,
        sort,
        search,
        filter,
        model,
        mapping_filters=None,
        period_mode="created_at",
    ):
        """
        Creates a new class with modified properties.
        """
        if mapping_filters is not None:
            ifilters = [
                scheme["filter"]
                for scheme in mapping_filters.values()
                if scheme.get("filter") is not None
            ]
        else:
            ifilters = []
        attributes = {
            "search": get_class_properties(search),
            "filter": get_class_properties([filter, *ifilters]),
            "sort": get_class_properties(sort),
            # могут быть значения Card__mv_order__avg_dynamics_quantity_in_1_day
            # они валидны? как используются?
            "read": get_class_properties(read),
            "model": model,
            # "ifilter": filter,
            # "isort": sort,
            # "isearch": search,
            "mapping_filters": mapping_filters,
            "period_mode": period_mode,
        }
        modified_props = {**self.Config.__dict__, **attributes}
        # todo можно для простоты дебага формировать уникальное имя
        return type(
            "ModifiedPaginateQueryParams",
            (self,),
            {"Config": type("Config", (), modified_props)},
        )

    @classmethod
    def update(
        self,
        read,
        sort,
        search,
        filter,
        model,
        mapping_filters=None,
        period_mode="created_at",
    ):
        """
        Creates a new class with modified properties.
        """
        if mapping_filters is not None:
            ifilters = [
                scheme["filter"]
                for scheme in mapping_filters.values()
                if scheme.get("filter") is not None
            ]
        else:
            ifilters = []
        attributes = {
            "search": get_class_properties(search),
            "filter": get_class_properties([filter, *ifilters]),
            "sort": get_class_properties(sort),
            # могут быть значения Card__mv_order__avg_dynamics_quantity_in_1_day
            # они валидны? как используются?
            "read": get_class_properties(read),
            "model": model,
            # "ifilter": filter,
            # "isort": sort,
            # "isearch": search,
            "mapping_filters": mapping_filters,
            "period_mode": period_mode,
        }
        modified_props = {**self.Config.__dict__, **attributes}
        # todo можно для простоты дебага формировать уникальное имя
        return type(
            "ModifiedPaginateQueryParams",
            (self,),
            {"Config": type("Config", (), modified_props)},
        )

    @classmethod
    def _get_model(cls, model_name):
        if (
            cls.Config.mapping_filters is not None
            and (local_mapping := cls.Config.mapping_filters.get(model_name))
            is not None
        ):
            # todo мб кейсы где несколько моделей, основная модель с этих случаях всегда первая?
            return local_mapping["model"][0]
        else:
            from app.common.model_map import straight_model_map

            return straight_model_map[model_name]["model"]

    @classmethod
    def _parse_join_column(cls, column: str) -> tuple[str, str, str | None]:
        # todo пока не понятно будут ли тут случаи под свою модель, кажется лучше сразу предусмотреть,
        #  чтобы своя модель тоже обрабатывалась, раньше своя модель была без префикса в названии колонки,
        #  сейсас у неё тоже есть префикс, пока он автогенерируемый, важно что здесь ждём такой же как сгенерировали

        # column = column.replace("__", ".")
        join_path = None
        if "__" in column:
            model_name, column_name = column.split("__")
            model = cls._get_model(model_name)
            mapping_filters = cls.Config.mapping_filters
            if mapping_filters is not None:
                join_path = cls.Config.mapping_filters.get(model_name, {}).get("path")
        else:
            camel_case_model_name = getattr(cls.Config, "model", None)
            if camel_case_model_name is None:
                raise ValueError("Config.model is not set")
            model = getattr(models, camel_case_model_name)
            column_name = column
        # column_name = param[1]

        return model, column_name, join_path

    @validator("search")
    def validator_search(cls, value: str | None) -> tuple | None:
        if value is None:
            return None
        result = []
        search_columns: KeysView[str] = (cls.Config.search or {}).keys()
        if not search_columns:
            raise ValidationException(detail="Search is not available here")
        try:
            search_list: list = StringSearch.parse_obj(value).dict()
            # Нет валидации, колонки берем из ISearch. Все строки были допустимы для поиска

            for column_name in search_columns:
                model, column, join_path = cls._parse_join_column(column_name)
                # value одинаковое для всех записей
                result.append(
                    {
                        "column": column,
                        "value": search_list,
                        "model": model,
                        "path": join_path,
                    }
                )
            return tuple(result)
        except Exception as e:
            raise ValidationException(detail=f"Search error processing: {e}")

    @validator("scope")
    def validator_scope(cls, value: str | None) -> str | None:
        """Не будет в стартовой версии"""
        return value

    @validator("period")
    def validator_period(cls, value: str | None) -> dict[str, str | None | Any] | None:
        if value is None:
            return None
        try:
            parsed_period: str = PeriodFilter.parse_obj(value).dict()
            model, column, join_path = cls._parse_join_column(cls.Config.period_mode)
            return {
                "column": column,
                "value": parsed_period,
                "model": model,
                "path": join_path,
            }
        except ValueError:
            raise ValidationException(
                detail="Can't process period value: format is YYYY-MM-DD:YYYY-MM-DD"
            )

    @root_validator
    def check_double_sort(cls, values):
        if values["ascending"] is not None and values["descending"] is not None:
            raise ValidationException(detail="Can not apply two sorts")
        return values

    @validator("ascending", "descending")
    def validator_sort(cls, value) -> None | list[dict[str, Any]]:
        if value is None:
            return None
        column_name: str = StringSort.parse_obj(value).dict()
        config_sort: dict = cls.Config.sort or {}
        if format_key(column_name, cls.Config.model) not in config_sort:
            raise ValidationException(
                detail=f"Invalid sort column: {value}. Possible values are: {config_sort.keys()}"
            )
        model, column, join_path = cls._parse_join_column(column_name)
        return [{"column": column, "value": None, "model": model, "path": join_path}]

    @validator("gt", "lt", "eq")
    def validator_gt_lt_eq(cls, value) -> list[dict[str, str | None | Any]] | None:
        if value is None:
            return None
        result = []
        try:
            value = DigitFilter.parse_obj(value).dict()
            for column_name, column_value in value.items():
                model, column, join_path = cls._parse_join_column(column_name)
                config_filter: dict = cls.Config.filter or {}
                annotation = config_filter.get(
                    format_key(column_name, cls.Config.model)
                )
                if annotation is None:
                    raise ValidationException(
                        detail=f"Invalid {column_name} number filter."
                    )
                # для цифровых фильтров теперь пишем ifilter аннотацию!
                column_value = validate_field_external(annotation, column_value)
                result.append(
                    {
                        "column": column,
                        "value": column_value,
                        "model": model,
                        "path": join_path,
                    }
                )
        except json.JSONDecodeError as e:
            raise ValidationException(detail=f"gt_lt_eq invalid format: {e}")
        except Exception as e:
            raise ValidationException(detail=f"gt_lt_eq error processing: {e}")
        return result

    @validator("column")
    def validator_column(cls, value: str | None) -> str | None:
        """Плейсхолдер пока filters в column не переименован"""
        return value

    @validator("filters")
    def validator_filters(cls, value: str | None) -> Optional[Any]:  # todo аннотация
        if value is None:
            return None
        result = []
        try:
            string_filter: dict = StringFilter.parse_obj(value).dict()
            for column_name, column_value in string_filter.items():
                model, column, join_path = cls._parse_join_column(column_name)
                # column_name = format_key(column_name, cls.Config.model)
                config_filter: dict = cls.Config.filter or {}
                annotation = config_filter.get(
                    format_key(column_name, cls.Config.model)
                )
                if annotation is None:
                    raise ValidationException(detail=f"Invalid {column_name} filter.")
                column_value = validate_field_external(annotation, column_value)
                # возвращаем модель явно, чтобы не потерять переопределение в mapping_filters
                result.append(
                    {
                        "column": column,
                        "value": column_value,
                        "model": model,
                        "path": join_path,
                    }
                )
        except:
            raise

        return tuple(result)

    def get_filters_schema(self) -> str:
        list_filters = {
            "search": self.search,
            "period": self.period,
            "scope": self.scope,
            "ascending": self.ascending,
            "descending": self.descending,
            "gt": self.gt,
            "lt": self.lt,
            "eq": self.eq,
            "column": self.column,
            "filters": self.filters,
        }
        list_filters = {x: y for x, y in list_filters.items() if y}
        return str(list_filters)


DataType = TypeVar("DataType")


class ImageUrl(BaseModel):
    url: str

    @root_validator
    def validate(cls, value):
        if value.get("url", False):
            if "http" not in value["url"]:
                value["url"] = f"{settings.URL}/media/{value['url']}"
        return value


class ImageOptimizedUrl(BaseModel):
    url: str

    @root_validator
    def validate(cls, value):
        if value.get("url", False):
            value["url"] = f"{settings.URL}/media/{value['url']}_optimized"
        return value


class BaseMeta(BaseModel):
    pass


class IResponseBase(GenericModel, Generic[DataType]):
    message: str = ""
    meta: dict | BaseMeta = {}
    data: Optional[list[DataType] | DataType] = None
    headers = {"X-UI-TOAST": "false"}


class IGetResponseBase(IResponseBase[DataType], Generic[DataType]):
    message: str = "Данные успешно получены"


class IPostResponseBase(IResponseBase[DataType], Generic[DataType]):
    message: str = "Данные успешно добавлены"


class IPutResponseBase(IResponseBase[DataType], Generic[DataType]):
    message: str = "Данные успешно обновлены"
    headers = {"X-UI-TOAST": "true"}


class IDeleteResponseBase(IResponseBase[DataType], Generic[DataType]):
    message: str = "Данные успешно удалены"
    headers = {"X-UI-TOAST": "true"}


class IPostResponseIntegration(IResponseBase[DataType], Generic[DataType]):
    message: str = "Данные успешно добавлены"
    integration_response: list = []


class IPutResponseIntegration(IResponseBase[DataType], Generic[DataType]):
    message: str = "Данные успешно обновлены"
    integration_response: dict | list | None = {}


class INotificationResponseBase(IResponseBase[DataType], Generic[DataType]):
    # не понятно, почему meta - это список, но иначе падает тест test_price.py::Test::test_update_cost_final
    meta: list | BaseMeta = {}  # type: ignore
    notification_type = ""
    button: str = "ОК"


class BaseFilter(BaseModel):
    _empty_str_to_none = validator("*", pre=True, allow_reuse=True)(empty_str_to_none)


class BaseSort(BaseModel):
    _empty_str_to_none = validator("*", pre=True, allow_reuse=True)(empty_str_to_none)
    updated_at: Optional[datetime]
    created_at: Optional[datetime]


class BaseUpdate(BaseModel):
    _empty_str_to_none = validator("*", pre=True, allow_reuse=True)(empty_str_to_none)


class IBaseUser(BaseModel):
    id: UUID
    email: Optional[str] = None


class RoundedFloat2DP(float):
    """
    Rounded float number with two decimal places
        Example:
        >>> RoundedFloat2DP(1.234567)
        1.23
        >>> RoundedFloat2DP(1.796331)
        1.8
    """

    @classmethod
    def validate(cls, value: Any) -> float:
        return super().__new__(cls, round(float(value), 2))

    @classmethod
    def __get_validators__(cls):
        yield cls.validate


class FloatToInt(float):
    """
    Rounded float number to integer
        Example:
        >>> FloatToInt(1.234567)
        1
        >>> FloatToInt(1.796331)
        2
    """

    @classmethod
    def validate(cls, value: Any) -> float:
        return super().__new__(cls, round(float(value), 0))

    @classmethod
    def __get_validators__(cls):
        yield cls.validate


"""**********************************************"""


class IntWithPercentage(str):
    """
    Integer with percentage sign
        Example:
        >>> IntWithPercentage(10)
        10%
        >>> IntWithPercentage(20)
        20%
    """

    @classmethod
    def validate(cls, value: Any) -> str:
        return f"{int(value)} %"

    @classmethod
    def __get_validators__(cls):
        yield cls.validate


class RoundedFloat2DPWithPercentage(str):
    """
    Number with percentage sign
        Example:
        >>> RoundedFloat2DPWithPercentage(1.234567)
        1.23 %
        >>> RoundedFloat2DPWithPercentage(1.796331)
        1.80 %
        >>> RoundedFloat2DPWithPercentage("1.234567")
        1.23 %
    """

    @classmethod
    def validate(cls, value: Any) -> str:
        return f"{round(float(value), 2)} %"

    @classmethod
    def __get_validators__(cls):
        yield cls.validate


class RoundedFloat2DPWithRUB(str):
    """
    Number with percentage sign
        Example:
        >>> RoundedFloat2DPWithPercentage(1.234567)
        1.23 р.
        >>> RoundedFloat2DPWithPercentage(1.796331)
        1.80 р.
        >>> RoundedFloat2DPWithPercentage("1.234567")
        1.23 р.
    """

    @classmethod
    def validate(cls, value: Any) -> str:
        return f"{round(float(value), 2)} р."

    @classmethod
    def __get_validators__(cls):
        yield cls.validate


class Country(str):
    """Список стран хранится в константах.

    Аннотация country: [Literal[*list[constants.COUNTRY.values()]]]
    не сработает, потому что при инициализации схем словарь constants.COUNTRY ещё пустой.
    Он заполнится только при прогреве кеша некоторое время спустя после загрузки приложения.
    """

    @classmethod
    def validate(cls, value: Any) -> Optional[str]:
        # Обработка колонки фронта с заданными доступными значениями.
        #
        # Если в available_values передать список ["россия", "китай"], то при фильтрации фронт будет отдавать индекс
        # списка в качестве ключа фильтрации, например "1" для "китай".
        # Исторически сложилось что в этом случае передаём словарь {"ru": "россия", "cn": "китай"}
        # и в валидаторе подставлением значение, например "россия" для "ru".
        #
        # Для фильтров можно создать отдельный тип, например, CountryFilter и приводить значения только в нём.
        # Для компактности обработка
        #     value = constants.COUNTRY.get(value, value)
        # добавлена в основной тип Country
        value = constants.COUNTRY.get(value, value)

        if value is not None and value not in constants.COUNTRY.values():
            # assert False
            # здесь не используется assert, вместо raise для вывода кастомной ошибки
            # должен быть лучший способ
            raise ValidationException(detail=f"Invalid country: {value}")
        return value

    @classmethod
    def __get_validators__(cls):
        yield cls.validate


class ReportResponse(BaseModel):
    content: bytes
    headers: dict = {"Content-Disposition": 'attachment; filename="{file_name}"'}
    media_type: str = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


class ITimeseries(BaseModel):
    label: list[str]  # ["заказы", "продажи", "выручка", "прибыль]
    date: list[str]  # ["2021-01-01", "2021-01-02", "2021-01-03", "2021-01-04"]
    data: list[list[int]]  # [[1, 2, 1, 2], [1, 2, 1, 2], [1, 2, 1, 2], [1, 2, 1, 2]]


class DateTimeMSK(datetime):
    @classmethod
    def validate(cls, value: Any) -> datetime:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value)
        elif isinstance(value, datetime):
            dt = value
        else:
            raise ValidationException(detail=f"Invalid datetime format {value}")

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        msk_tz = ZoneInfo("Europe/Moscow")
        dt = dt.astimezone(msk_tz)
        return dt

    @classmethod
    def __get_validators__(cls):
        yield cls.validate
