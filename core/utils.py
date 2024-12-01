import asyncio
import base64
import random
import re
import string
import struct
from typing import Any, Awaitable, Dict, Optional, Type, TypeVar, Union
from uuid import UUID

import six
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import (
    RSAPrivateNumbers,
    RSAPublicNumbers,
    rsa_crt_dmp1,
    rsa_crt_dmq1,
    rsa_crt_iqmp,
)
from cryptography.hazmat.primitives.serialization import NoEncryption
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi_pagination.api import create_page, resolve_params
from fastapi_pagination.bases import AbstractPage, AbstractParams
from sqlalchemy.engine.row import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func, select
from sqlalchemy.sql.selectable import Select, SelectBase
from starlette.background import BackgroundTask

from app.common.model_map import reversed_model_map
from core.exceptions import BadRequestException, BaseAPIException, ValidationException

__all__ = (
    "jwk2pem",
    "empty_str_to_none",
    "make_response",
    "round_2_or_none",
    "escape_special_chars_for_tsquery",
    "paginate",
    "separate_nulls",
    "flatten_single_element_row",
    "rnd_str",
    "parse_id",
)


def rnd_str(source_chars=string.ascii_uppercase + string.digits, k=10):
    return "".join(random.choices(source_chars, k=k))


class Base:
    pass


T = TypeVar("T", bound=Base)


def clean_statuses(data):
    manager_status = data.get("manager_status")
    if isinstance(manager_status, Dict):
        data["manager_status"] = manager_status["value"]
    status = data.get("status")
    if isinstance(status, Dict):
        data["status"] = status["value"]
    return data


def empty_str_to_none(cls, v):
    pass
    if v in (""):
        return None

    if isinstance(v, list):
        return [None if x in ("", "null") else x for x in v]
    return v


def round_2_or_none(value):
    if value is None:
        return None
    return round(value, 2)


def str_to_bool(val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.
    Raises ValueError if 'val' is anything else.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))


class CustomHeadersJSONResponse(JSONResponse):
    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        background: Optional[BackgroundTask] = None,
    ) -> None:
        if isinstance(content, dict) and (custom_headers := content.pop("headers", None)):
            headers = headers or {}
            headers.update(custom_headers)

        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )


async def limited_gather(*awaitables: Awaitable, limit: int = 30, return_exceptions: bool = False) -> list:
    """
    Gather task using semaphore. Default limit is 30.

    Args:
        awaitables (Awaitable): awaitable objects
        limit (int, optional): limit of concurrent tasks. Defaults to 30.
        return_exceptions (bool, optional): return exceptions. Defaults to False.

    Returns:


    Example:
        import asyncio
        import random

        async def some_task(i: int) -> int:
            random_sleep = random.randint(1, 5)
            print(f'Running task {i}, wait {random_sleep}s.')
            await asyncio.sleep(random_sleep)
            print(f'Finish task {i}.')
            return i

        await limit_gather(*[some_task(i) for i in range(10)], limit=3)

    Example output:
        Running task 0, wait 4s.
        Running task 1, wait 4s.
        Running task 2, wait 2s.
        Finish task 2.
        Running task 3, wait 1s.
        Finish task 3.
        Running task 4, wait 5s.
        Finish task 0.
        Finish task 1.
        Running task 5, wait 1s.
        Running task 6, wait 2s.
        Finish task 5.
        Running task 7, wait 2s.
        Finish task 6.
        Running task 8, wait 5s.
        Finish task 7.
        Finish task 4.
        Finish task 8.
        [0, 1, 2, 3, 4, 5, 6, 7, 8]
    """
    semaphore = asyncio.Semaphore(limit)

    async def _with_semaphore(awaitable: Awaitable):
        async with semaphore:
            return await awaitable

    return await asyncio.gather(
        *(_with_semaphore(awaitable) for awaitable in awaitables),
        return_exceptions=return_exceptions,
    )


def flatten_single_element_row(items):
    if items and isinstance(items[0], Row) and len(items[0]) == 1:
        # todo разобраться почему раньше row из одного элемента распаковывалась сама в Pydantic
        items = [x[0] for x in items]

    return items


async def exec_count(
    db_session: AsyncSession,
    query: Optional[Select],
):
    # total_query = select(func.count("*")).select_from(query.order_by(None).subquery())

    count_query = query.with_only_columns(func.count(), maintain_column_froms=True).order_by(None)
    # from sqlalchemy.dialects import postgresql
    # some = str(count_query.compile(dialect=postgresql.dialect()))
    response = await db_session.execute(count_query)
    return response.scalar()


async def paginate(
    db_session: AsyncSession,
    query: Union[T, Select, SelectBase],
    params: Optional[AbstractParams] = None,
) -> AbstractPage[T]:
    params = resolve_params(params)
    raw_params = params.to_raw_params()

    if not isinstance(query, (Select, SelectBase)):
        query = select(query)
    total = await exec_count(db_session, query)
    query_response = await db_session.execute(query.limit(raw_params.limit).offset(raw_params.offset))
    items = query_response.unique().all()
    items = flatten_single_element_row(items)
    return create_page(items, total, params)


class ModelMetaOptions:
    def __init__(self, options=None):
        self.fields = getattr(options, "fields", {})


def jwk2pem(jwk):
    def intarr2long(arr):
        return int("".join(["%02x" % byte for byte in arr]), 16)

    def base64_to_long(data):
        if isinstance(data, six.text_type):
            data = data.encode("ascii")
        # urlsafe_b64decode will happily convert b64encoded data
        _d = base64.urlsafe_b64decode(bytes(data) + b"==")
        return intarr2long(struct.unpack("%sB" % len(_d), _d))

    e = base64_to_long(jwk["e"])
    n = base64_to_long(jwk["n"])
    p = base64_to_long(jwk["p"])
    q = base64_to_long(jwk["q"])
    d = base64_to_long(jwk["d"])
    dmp1 = rsa_crt_dmp1(d, p)
    dmq1 = rsa_crt_dmq1(d, q)
    iqmp = rsa_crt_iqmp(p, q)

    public_numbers = RSAPublicNumbers(e, n)
    private_numbers = RSAPrivateNumbers(p, q, d, dmp1, dmq1, iqmp, public_numbers)

    public_key = public_numbers.public_key(backend=default_backend())
    private_key = private_numbers.private_key(backend=default_backend())

    pem_public_key = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    pem_private_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )
    return {"PEM_PUBLIC_KEY": pem_public_key, "PEM_PRIVATE_KEY": pem_private_key}


def parse_id(id: str) -> list[UUID]:
    id_parts = id.split(".")
    try:
        id_list = [UUID(part) for part in id_parts]
    except ValueError:
        raise ValidationException(detail="Invalid UUID format or value")
    return id_list


def camel_to_snake(name: str) -> str:

    return reversed_model_map.get(name) or name[0].lower() + "".join(
        x if x.islower() else f"_{x.lower()}" for x in name[1:]
    )


def format_key(key: str, scheme) -> str:
    if "__" in key:
        return key
    scheme_name = scheme if isinstance(scheme, str) else scheme.__model_name__
    # todo даблчек что все mapping_filters именования соответствуют reversed_model_map
    return f"{camel_to_snake(scheme_name)}__{key}"


def validate_field_external(annotation, value):
    parsed, error = annotation.validate(value, {}, loc=None)
    if error is None:
        # todo лучше райзить ошибку, выделить время на тесты и возможно правку упавших схем.
        value = parsed
    return value


def get_class_properties(schemas: Type | list[Type]) -> dict:  # не понятно в каких случаях список классов в каких один
    result = {}
    if not isinstance(schemas, list):
        schemas = [schemas]

    for scheme in schemas:
        # if scheme.__name__ == "MVStockownerForCard":
        #     pass
        try:
            # нет запрета описывать в схеме поля другой схемы могут быть перезатирания
            formatted_hints = {format_key(key, scheme): value for key, value in scheme.__fields__.items()}
        except AttributeError:
            raise ValueError("Invalid class")
        result.update(formatted_hints)
    return result


def escape_special_chars_for_tsquery(string: str) -> str:
    # Regex pattern to match special characters that need to be escaped in tsquery
    pattern = r'([&|"\':!*()])'
    # Replace each special character with its escaped version
    return re.sub(pattern, r"\\\1", string)


def separate_nulls(values: list) -> tuple[list, bool]:
    null_values = (None, "", [None])  # todo какие кейсы на [None]?
    significant_values = [v for v in values if v not in null_values]
    nulls = len(significant_values) != len(values)
    return significant_values, nulls


def default_trier():
    """Кажется что проще использовать подобную зависимость или написать свой менеджер контекста.

    Что бы не повторять try/except/BadRequestException везде
    """
    try:
        yield
    except BaseAPIException:
        raise
    except Exception as exc:
        raise BadRequestException(detail=str(exc))


def make_response(response_model, **kwargs):
    """Подавление множественной валидации модели ответа.

    https://github.com/tiangolo/fastapi/issues/1406#issuecomment-1304556397
    Параметр response_model валидирует модель второй раз. При сложном описании схемы может быть 3 и больше повторов.
    На второй и последющих итерациях на вход подаётся результат предыдущей валидации.
    Т.е result = validata(validate(validate(data)) вместо validate(data)
    Если в return роута возвращается Response тип, то избыточные валидации пропускаются.
    А в описании OpenApi Docs останется модель из response_model.

    https://docs.pydantic.dev/1.10/blog/pydantic-v2/#model-namespace-cleanup
    """
    validated_data = response_model(**kwargs)
    json_compatible_item_data = jsonable_encoder(validated_data)
    return CustomHeadersJSONResponse(content=json_compatible_item_data)


def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.
    Raises ValueError if 'val' is anything else.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1", "да", "да*"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0", "нет", "нет*"):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))
