from app.cargo_insurance.model import CargoInsurance
from app.cargo_insurance.schema import ICreate, IUpdate
from core.base.crud import CRUDBase


class CRUD(CRUDBase[CargoInsurance, ICreate, IUpdate]): ...


cargo_insurance = CRUD(CargoInsurance)
