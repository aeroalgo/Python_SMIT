from sqlalchemy import TIMESTAMP, Column, Double, String
from sqlalchemy.dialects.postgresql import UUID as UUID_PG
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship

from core.base.model import Base, BaseUUIDModel

__all__ = (
    "CargoInsuranceBase",
    "CargoInsurance",
)


class CargoInsuranceBase:
    cargo_type = Column(String, nullable=True)
    rate = Column(Double, nullable=True, index=True)
    date = Column(TIMESTAMP, nullable=True)


class CargoInsurance(CargoInsuranceBase, BaseUUIDModel, Base):
    __table_args__ = {
        "comment": "CargoInsuranceBase",
        "schema": "public",
    }
    __tablename__ = "CargoInsurance"
