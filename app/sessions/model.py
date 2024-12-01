import uuid

from sqlalchemy import (
    TIMESTAMP,
    Column,
    ForeignKey,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as UUID_PG
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship

from core.base.model import Base


__all__ = (
    "SessionsBase",
    "Sessions",
)


class SessionsBase:

    id = Column(
        UUID_PG(as_uuid=True),
        primary_key=True,
        index=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    cookie = Column(String)
    access_token = Column(String)
    refresh_token = Column(String)
    token_type = Column(String, default="bearer")
    expires_at = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=func.now())

    @declared_attr
    def user_id(cls):
        return Column(
            UUID_PG(as_uuid=True), ForeignKey("public.user.id", ondelete="CASCADE")  # , name="auth.sessions.user_id"
        )


class Sessions(SessionsBase, Base):
    __table_args__ = {"comment": "Sessions", "schema": "public"}
    __tablename__ = "sessions"
    user = relationship(
        "User", back_populates="sessions", lazy="select"
    )  # primaryjoin="and_(Sessions.user_id==User.id)",
