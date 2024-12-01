from sqladmin import Admin, ModelView

from app.model import Product, Resource, Role, Sessions, Team, User, Visibility_Group
from core.database.database import async_engine

__all__ = (
    "UserAdmin",
    "SessionsAdmin",
)


class UserAdmin(ModelView, model=User):
    name_plural = "Users"
    # column_exclude_list = form_excluded_columns = [
    #     User.title,
    # ]


class SessionsAdmin(ModelView, model=Sessions):
    name_plural = "Sessions"


async def init_admin(app):
    admin = Admin(app, async_engine, base_url="/auth/admin")
    models = [
        UserAdmin,
        SessionsAdmin,
    ]

    for model in models:
        admin.add_view(model)
