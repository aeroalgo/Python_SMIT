from typing import Optional

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    expires_at: int  # Unix timestamp in seconds
    token_type: str
    refresh_token: Optional[str]


class RefreshToken(BaseModel):
    refresh_token: str


class IPassword(BaseModel):
    password: str
