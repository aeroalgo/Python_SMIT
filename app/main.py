import asyncio
from fastapi import FastAPI

from api.v1.api import router
from core.database.database import init_database  # noqa
from core.logger import logger
from core.middleware import (  # noqa
    ContextMiddleware,
    CustomExceptionMiddleware,
    CustomHeaderMiddleware,
)
from core.settings import settings
from core.utils import CustomHeadersJSONResponse


# sentry_init()

app = FastAPI(
    title="cargo",
    description="Cargo tarif backend service",
    version="1.0.0",
    openapi_url="/openapi.json",
    openapi_tags=[
        {
            "name": "Cargo",
            "description": "Cargo tarif backend service",
        }
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    default_response_class=CustomHeadersJSONResponse,
)
app.include_router(router)

# app.add_middleware(CustomExceptionMiddleware)
app.add_middleware(CustomHeaderMiddleware)
app.add_middleware(ContextMiddleware)
handler = None
is_on_startup = False


async def on_startup():
    logger.debug("on_startup: started")
    global is_on_startup
    logger.debug(f"is_on_startup: {is_on_startup}")
    if is_on_startup:
        logger.debug("on_startup: skipped")
        return
    await asyncio.gather(
        init_database(),
    )
    is_on_startup = True
    logger.debug("on_startup: completed")


app.on_event("startup")(on_startup)
