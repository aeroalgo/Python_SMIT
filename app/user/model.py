from sqlalchemy import Boolean, Column, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as UUID_PG
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression
from sqlalchemy.types import ARRAY

from core.base.model import Base, BaseUUIDModel

__all__ = (
    "User",
    "UserBase",
)


class UserBase:
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True, unique=True)
    hashed_password = Column(String, nullable=True, comment="Хэш пароля")
    is_active = Column(Boolean, server_default=expression.true())
    is_staff = Column(Boolean, server_default=expression.false(), nullable=True)
    is_superuser = Column(Boolean, server_default=expression.false(), nullable=True)
    allow_basic_login = Column(
        Boolean, server_default=expression.false(), nullable=True
    )
    aliases = Column(ARRAY(String), nullable=True)
    picture = Column(String, nullable=True)


class User(BaseUUIDModel, UserBase, Base):
    __table_args__ = {"comment": "User", "schema": "public"}
    __tablename__ = "user"
    sessions = relationship(
        "Sessions",
        cascade="all, delete",
        uselist=True,
        lazy="select",
    )
