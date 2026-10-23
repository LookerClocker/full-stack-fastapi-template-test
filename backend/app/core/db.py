from sqlmodel import Session, create_engine

from app import crud
from app.core.config import settings
from app.core.rbac import Role
from app.models import User, UserCreate

engine = create_engine(str(settings.DATABASE_URL), pool_pre_ping=True)

DEMO_USER_EMAILS: dict[Role, str] = {
    Role.MANAGER: "manager@example.com",
    Role.MEMBER: "member@example.com",
}


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    ensure_user(
        session,
        email=settings.FIRST_SUPERUSER,
        password=settings.FIRST_SUPERUSER_PASSWORD,
        role=Role.ADMIN,
    )
    # Demo accounts have a shared, well-known password: never seed them outside development.
    if settings.FASTAPI_ENV == "development" and settings.DEMO_USER_PASSWORD:
        for role, email in DEMO_USER_EMAILS.items():
            ensure_user(
                session, email=email, password=settings.DEMO_USER_PASSWORD, role=role
            )


def ensure_user(session: Session, *, email: str, password: str, role: Role) -> User:
    user = crud.get_user_by_email(session=session, email=email)
    if user:
        return user
    user_in = UserCreate(email=email, password=password, role=role)
    return crud.create_user(session=session, user_create=user_in)
