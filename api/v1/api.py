from importlib import import_module

from fastapi import APIRouter


names = (
    "auth",
    "sessions",
    "user",
    "cargo_insurance"
)

__all__ = ("router",)

modules = (import_module(f"api.v1.endpoints.{name}") for name in names)

router = APIRouter(prefix="/api/v1")
for path_module in modules:
    # print(f"Importing {path_module.__name__}")
    ro = path_module.router
    # print(f"Adding {ro.prefix}")
    router.include_router(ro)

# print all the routes
# for i in router.routes:
#     print(i.path)
