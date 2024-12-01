import json
import os
from pathlib import Path
from typing import Any, Dict, Literal, Optional
from urllib.parse import urljoin

from pydantic import BaseSettings, root_validator, validator

from core.utils import jwk2pem

ROOT_DIR = os.path.dirname(os.path.abspath(os.curdir))
SECRETS_PATH = {
    "dev": f"{ROOT_DIR}/docker/dev/.env",
    "local": f"{ROOT_DIR}/.env",
}
SECRETS_PROVIDER: Optional[Literal["aws", "yc", "dev", "prod", "local"]] = "local"


class Settings(BaseSettings):
    URL: str
    APP_PORT: int
    PSQL_USER: str
    PSQL_PASS: str
    PSQL_DB: str
    PSQL_HOST: str
    PSQL_PORT: int
    KAFKA_HOST: str
    KAFKA_PORT: int
    JWK: str
    PRODUCE_TOPIC: str
    PEM_PUBLIC_KEY: str = None
    PEM_PRIVATE_KEY: str = None
    PSQL_ASYNC_URL: str = None

    @validator("PSQL_ASYNC_URL")
    def assemble_db_async_connection(
        cls, value: Optional[str], values: Dict[str, Any]
    ) -> Any:
        if isinstance(value, str):
            return value
        return (
            f"postgresql+asyncpg://{values.get('PSQL_USER')}:"
            f"{values.get('PSQL_PASS')}@{values.get('PSQL_HOST')}:"
            f"{values.get('PSQL_PORT')}/{values.get('PSQL_DB')}"
        )

    @root_validator
    def extract_jwk(cls, values):
        print(values)
        keys = jwk2pem(json.loads(values["JWK"]))
        values["PEM_PUBLIC_KEY"] = keys["PEM_PUBLIC_KEY"]
        values["PEM_PRIVATE_KEY"] = keys["PEM_PRIVATE_KEY"]
        return values

    @property
    def token_url(self):
        """Get token url for OAuth2PasswordBearer."""
        url = getattr(self, "URL", None)
        if not url:
            raise AttributeError("URL is not set.")
        return urljoin(url, "/api/v1/auth/basic")

    class Config:

        env_file = SECRETS_PATH.get(SECRETS_PROVIDER)


settings = Settings()
