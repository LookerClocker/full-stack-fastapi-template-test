# Backend blueprint

All paths relative to `backend/`. Python 3.14, mypy strict. These snippets were type-checked against this project's toolchain.

## §1 `app/core/rbac.py` (new) — the whole authorization model in one file

```python
"""Roles, permissions, and which role holds which permission.

This module is the single source of truth for authorization policy. Code elsewhere
asks "does this user have permission X?" and never "is this user role Y?".
"""

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"


class Permission(StrEnum):
    USERS_READ = "users:read"
    USERS_CREATE = "users:create"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    METRICS_READ = "metrics:read"
    SETTINGS_MANAGE = "settings:manage"
    ITEMS_MANAGE_ALL = "items:manage_all"


# Anything not listed here is denied. Every authenticated user may always manage
# their own profile and their own items; those need no permission.
ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    Role.MANAGER: frozenset({Permission.USERS_READ, Permission.METRICS_READ}),
    Role.MEMBER: frozenset(),
}


def permissions_for(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in permissions_for(role)
```

Note: a `role` loaded from the DB is a plain `str`. `StrEnum` members hash and compare equal to their values, so `ROLE_PERMISSIONS["admin"]` works — do not add conversion code.

## §2 `app/models.py`

Imports to add:
```python
from pydantic import EmailStr, computed_field
from sqlalchemy import String

from app.core.rbac import Permission, Role, permissions_for
```

`UserBase` — replace `is_superuser: bool = False` with:
```python
    role: Role = Field(default=Role.MEMBER, sa_type=String(length=20))
```

`UserUpdate` — replace `is_superuser: bool | None = None` with:
```python
    role: Role | None = None
```

`UserRegister` and `UserUpdateMe` — must **not** gain a `role` field (self-escalation guard). Leave them as they are.

`UserPublic` — redeclare `role` without a default (otherwise OpenAPI marks it optional and the generated TS type becomes `role?: Role`), and add the derived capability list the frontend reads:
```python
class UserPublic(UserBase):
    id: uuid.UUID
    role: Role
    created_at: datetime | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def permissions(self) -> list[Permission]:
        return sorted(permissions_for(self.role))
```

Add next to the other response schemas:
```python
class MetricsPublic(SQLModel):
    total_users: int
    active_users: int
    total_items: int
    users_by_role: dict[Role, int]
```

## §3 `app/core/config.py` and `app/api/deps.py`

`config.py` — in `Settings`, next to `FIRST_SUPERUSER_PASSWORD`:
```python
    # Seeds manager@example.com and member@example.com, in development only.
    DEMO_USER_PASSWORD: str | None = None
```
and in `_enforce_non_default_secrets`, after the `FIRST_SUPERUSER_PASSWORD` check:
```python
        self._check_default_secret("DEMO_USER_PASSWORD", self.DEMO_USER_PASSWORD)
```

`deps.py`:
- Add `import logging`, `from collections.abc import Callable, Generator`, and `from app.core.rbac import Permission, has_permission`. Add `logger = logging.getLogger(__name__)` after imports.
- In `get_current_user`, change the invalid-token error to **401**:
```python
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
```
- **Delete** `get_current_active_superuser`. Add at the end of the file:
```python
def ensure_permission(user: User, permission: Permission) -> None:
    if has_permission(user.role, permission):
        return
    logger.warning(
        "Permission denied: user_id=%s role=%s permission=%s",
        user.id,
        user.role,
        permission,
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to perform this action",
    )


def require_permission(permission: Permission) -> Callable[[User], User]:
    """Route dependency: `dependencies=[Depends(require_permission(Permission.X))]`."""

    def check_permission(current_user: CurrentUser) -> User:
        ensure_permission(current_user, permission)
        return current_user

    return check_permission
```

## §4 Migration

Create: `.claude/scripts/dev.sh migration "Replace is_superuser with role"`. Fill the generated file's bodies (keep its header and revision ids; `down_revision` must be `fe56fa70289e`, or the current head if newer):

```python
def upgrade():
    op.add_column(
        "user",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="member"),
    )
    op.execute("""UPDATE "user" SET role = 'admin' WHERE is_superuser""")
    op.drop_column("user", "is_superuser")


def downgrade():
    op.add_column(
        "user",
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("""UPDATE "user" SET is_superuser = true WHERE role = 'admin'""")
    op.drop_column("user", "role")
```
Ensure `import sqlalchemy as sa` is present. Then `.claude/scripts/dev.sh migrate`.

## §5 `app/api/routes/users.py`

Imports: replace `get_current_active_superuser` with `require_permission`; add `from app.core.rbac import Permission, Role`.

| Endpoint | Change |
|---|---|
| `GET /` `read_users` | `dependencies=[Depends(require_permission(Permission.USERS_READ))]` |
| `POST /` `create_user` | `dependencies=[Depends(require_permission(Permission.USERS_CREATE))]` |
| `GET /{user_id}` `read_user_by_id` | Keep "self → return"; replace the `if not current_user.is_superuser: raise 403` block with `ensure_permission(current_user, Permission.USERS_READ)` (import it from deps). The 404 check stays **after** it. |
| `PATCH /{user_id}` `update_user` | `dependencies=[Depends(require_permission(Permission.USERS_UPDATE))]`; add `current_user: CurrentUser` param; after the 404 check add the lock-out guard below. |
| `DELETE /{user_id}` `delete_user` | `dependencies=[Depends(require_permission(Permission.USERS_DELETE))]`; keep the self-delete guard, message `"Admins are not allowed to delete themselves"`. |
| `DELETE /me` `delete_user_me` | Replace `if current_user.is_superuser` with `if current_user.role == Role.ADMIN`, message `"Admins are not allowed to delete themselves"`. |
| `/signup`, `/me` GET/PATCH, `/me/password` | No change (authenticated-only / public by design). `UserRegister` and `UserUpdateMe` have no `role`, so escalation is impossible. |

Lock-out guard for `update_user`:
```python
    if db_user.id == current_user.id and user_in.role not in (None, current_user.role):
        raise HTTPException(status_code=403, detail="You cannot change your own role")
```

## §6 Other routes

`items.py` — the three ownership checks and the list query use `current_user.is_superuser`. Add a small module-level helper and use it everywhere:
```python
from app.core.rbac import Permission, has_permission


def can_manage_all_items(user: User) -> bool:
    return has_permission(user.role, Permission.ITEMS_MANAGE_ALL)
```
`if current_user.is_superuser:` → `if can_manage_all_items(current_user):`
`if not current_user.is_superuser and (item.owner_id != current_user.id):` → `if not can_manage_all_items(current_user) and item.owner_id != current_user.id:`
(Import `User` from `app.models` if not already imported.)

`utils.py` `POST /test-email/` and `login.py` `POST /password-recovery-html-content/{email}`:
`dependencies=[Depends(require_permission(Permission.SETTINGS_MANAGE))]` (update imports; drop `get_current_active_superuser`).

`private.py` — no change: `User(...)` without `role` defaults to `member`.

## §7 `app/api/routes/metrics.py` (new) + registration

```python
from fastapi import APIRouter, Depends
from sqlmodel import Session, col, func, select

from app.api.deps import SessionDep, require_permission
from app.core.rbac import Permission, Role
from app.models import Item, MetricsPublic, User

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get(
    "/",
    dependencies=[Depends(require_permission(Permission.METRICS_READ))],
    response_model=MetricsPublic,
)
def read_metrics(session: SessionDep) -> MetricsPublic:
    """
    Aggregate user and item counts for the insights page.
    """
    return MetricsPublic(
        total_users=session.exec(select(func.count()).select_from(User)).one(),
        active_users=session.exec(
            select(func.count()).select_from(User).where(col(User.is_active))
        ).one(),
        total_items=session.exec(select(func.count()).select_from(Item)).one(),
        users_by_role=count_users_by_role(session),
    )


def count_users_by_role(session: Session) -> dict[Role, int]:
    rows = session.exec(
        select(col(User.role), func.count()).group_by(col(User.role))
    ).all()
    counts = {Role(role): count for role, count in rows}
    return {role: counts.get(role, 0) for role in Role}
```
Register in `app/api/main.py`: import `metrics` and add `api_router.include_router(metrics.router)` with the other routers (not inside the development-only block).

## §8 Seeding

`app/core/db.py` — keep the module's existing comments; replace the body of `init_db` and add a helper:
```python
from app.core.rbac import Role

DEMO_USER_EMAILS: dict[Role, str] = {
    Role.MANAGER: "manager@example.com",
    Role.MEMBER: "member@example.com",
}


def init_db(session: Session) -> None:
    # (keep the existing comments about Alembic / create_all here)
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
```
Remove the now-unused `select` import if nothing else uses it.

**Do not** put `DEMO_USER_PASSWORD` in `.env` or `compose.yml`. The tracked `.env` is read by both deploy workflows (and sets `FASTAPI_ENV=development`), so a value there would either crash the Compose deploy (default-secret check) or seed weak demo accounts in production via the FastAPI Cloud prestart step.

`compose.override.yml` (local only; deploys use `-f compose.yml -f compose.deploy.yml`) — in `services.backend.environment`, after `FASTAPI_ENV`:
```yaml
      # Local-only demo accounts (manager@example.com, member@example.com)
      DEMO_USER_PASSWORD: ${DEMO_USER_PASSWORD:-changethis}
```
Then `.claude/scripts/dev.sh seed`.
