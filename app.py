from dataclasses import dataclass
from datetime import datetime

import uvicorn
from litestar import Litestar
from litestar.config.csrf import CSRFConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.contrib.sqlalchemy.base import UUIDAuditBase, UUIDBase
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.contrib.sqlalchemy.plugins import (
    SQLAlchemyAsyncConfig,
    SQLAlchemyInitPlugin,
    SQLAlchemyPlugin,
)
from litestar.dto import DataclassDTO, DTOConfig
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.static_files import StaticFilesConfig
from litestar.template import TemplateConfig
from litestar_users import LitestarUsers, LitestarUsersConfig
from litestar_users.adapter.sqlalchemy.mixins import (
    SQLAlchemyRoleMixin,
    SQLAlchemyUserMixin,
)
from litestar_users.config import (
    AuthHandlerConfig,
    CurrentUserHandlerConfig,
    PasswordResetHandlerConfig,
    RegisterHandlerConfig,
    RoleManagementHandlerConfig,
    UserManagementHandlerConfig,
    VerificationHandlerConfig,
)
from litestar_users.guards import roles_accepted, roles_required
from litestar_users.password import PasswordManager
from litestar_users.service import BaseUserService
from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.exception import exception_config
from src.routes import serveHomepage, serveLogin, serveSecretShit

ENCODING_SECRET = "1234567890abcdef"  # noqa: S105
DATABASE_URL = "sqlite+aiosqlite:///"
password_manager = PasswordManager()


class Role(UUIDBase, SQLAlchemyRoleMixin):
    created_at = mapped_column(DateTime(), default=datetime.now)


class User(UUIDAuditBase, SQLAlchemyUserMixin):
    title: Mapped[str] = mapped_column(String(20))
    login_count: Mapped[int] = mapped_column(Integer(), default=0)

    roles: Mapped[Role] = relationship(
        "Role", secondary="user_role", lazy="selectin"
    )  # pyright: ignore


class UserRole(UUIDBase):
    user_id = mapped_column(Uuid(), ForeignKey("user.id"))
    role_id = mapped_column(Uuid(), ForeignKey("role.id"))


class RoleCreateDTO(SQLAlchemyDTO[Role]):
    config = DTOConfig(exclude={"id"})


class RoleReadDTO(SQLAlchemyDTO[Role]):
    pass


class RoleUpdateDTO(SQLAlchemyDTO[Role]):
    config = DTOConfig(exclude={"id"}, partial=True)


@dataclass
class UserRegistrationSchema:
    email: str
    password: str
    title: str


class UserRegistrationDTO(DataclassDTO[UserRegistrationSchema]):
    """User registration DTO."""


class UserReadDTO(SQLAlchemyDTO[User]):
    config = DTOConfig(exclude={"password_hash"})


class UserUpdateDTO(SQLAlchemyDTO[User]):
    # we'll update `login_count` in UserService.post_login_hook
    config = DTOConfig(exclude={"id", "login_count"}, partial=True)
    # we'll update `login_count` in the UserService.post_login_hook


class UserService(BaseUserService[User, Role]):  # pyright: ignore
    async def post_login_hook(
        self, user: User
    ) -> None:  # This will properly increment the user's `login_count`
        user.login_count += 1  # pyright: ignore


sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string=DATABASE_URL,
    session_dependency_key="session",
)


async def on_startup() -> None:
    """Initialize the database."""
    async with sqlalchemy_config.create_engine().begin() as conn:  # pyright: ignore
        await conn.run_sync(UUIDBase.metadata.create_all)

    admin_role = Role(name="administrator", description="Top admin")
    admin_user = User(
        email="admin@example.com",
        password_hash=password_manager.hash("iamsuperadmin"),
        is_active=True,
        is_verified=True,
        title="Exemplar",
        roles=[admin_role],
    )
    session_maker = sqlalchemy_config.create_session_maker()
    async with session_maker() as session, session.begin():
        session.add(admin_user)


litestar_users = LitestarUsers(
    config=LitestarUsersConfig(
        auth_backend="session",
        session_backend_config=ServerSideSessionConfig(),
        secret="sixteenbitssssss",  # noqa: S106
        sqlalchemy_plugin_config=sqlalchemy_config,
        user_model=User,  # pyright: ignore
        user_read_dto=UserReadDTO,
        user_registration_dto=UserRegistrationDTO,
        user_update_dto=UserUpdateDTO,
        role_model=Role,  # pyright: ignore
        role_create_dto=RoleCreateDTO,
        role_read_dto=RoleReadDTO,
        role_update_dto=RoleUpdateDTO,
        user_service_class=UserService,  # pyright: ignore
        auth_handler_config=AuthHandlerConfig(
            login_path="/api/login", logout_path="/api/logout"
        ),
        current_user_handler_config=CurrentUserHandlerConfig(),
        password_reset_handler_config=PasswordResetHandlerConfig(
            forgot_path="/api/forgot-password", reset_path="/api/reset-password"
        ),
        register_handler_config=RegisterHandlerConfig(path="/api/register"),
        role_management_handler_config=RoleManagementHandlerConfig(
            guards=[roles_accepted("administrator")]
        ),
        user_management_handler_config=UserManagementHandlerConfig(
            guards=[roles_required("administrator")]
        ),
        verification_handler_config=VerificationHandlerConfig(),
    )
)

# SEEMS LIKE CSRF DOESN"T WORK UNLESS YOU EXCLUDE THE LOGIN AND LOGOUT ROUTES
csrf_config = CSRFConfig(secret="IAMTOPSECRET", exclude=["/api/login", "/api/logout"])

app = Litestar(
    csrf_config=csrf_config,
    debug=True,
    on_app_init=[litestar_users.on_app_init],
    on_startup=[on_startup],
    plugins=[SQLAlchemyPlugin(config=sqlalchemy_config)],
    route_handlers=[serveHomepage, serveLogin, serveSecretShit],
    exception_handlers=exception_config,
    static_files_config=[
        StaticFilesConfig(
            directories=["src/static"],
            path="/src/static",
            opt={"skip_rate_limiting": True, "exclude_from_auth": True},
            name="static",
        ),
    ],
    template_config=TemplateConfig(
        directory="src/templates", engine=JinjaTemplateEngine
    ),
)

if __name__ == "__main__":
    uvicorn.run(app="with_roles:app", reload=True)
