---
paths:
  - "backend/**"
---

# Backend Rules (FastAPI / SQLModel / PostgreSQL)

## Layout — put code where its layer lives
| Layer | File | Holds |
|---|---|---|
| Domain policy | `app/core/rbac.py` | Roles, permissions, role→permission matrix. No FastAPI, no DB imports. |
| Config | `app/core/config.py` | Settings read from env / `.env`. |
| Models | `app/models.py` | SQLModel tables and API schemas (`*Base`, `*Create`, `*Update`, `*Public`). |
| Data access | `app/crud.py` | Reusable DB operations. |
| HTTP dependencies | `app/api/deps.py` | Session, current user, authorization dependencies. |
| Endpoints | `app/api/routes/<resource>.py` | One router per resource, registered in `app/api/main.py`. |
| Seeding | `app/core/db.py` (`init_db`) | Idempotent initial data. |

## Conventions
- Python 3.14, mypy `strict`, `ty`, Ruff. Fully type every function. No `Any` in new code except where the file already returns `Any` from route handlers.
- Endpoints declare authorization in the decorator: `dependencies=[Depends(require_permission(Permission.X))]`. Use in-handler checks only when the decision depends on the loaded resource (ownership, "self or permission").
- Request schemas define exactly what a caller may set. Privileged fields (e.g. `role`) never appear on self-service or public schemas (`UserRegister`, `UserUpdateMe`).
- Response schemas never include secrets (`hashed_password`).
- Use `HTTPException` with an explicit status code and a human-readable `detail`.
- Status codes: 400 invalid request, 401 missing/invalid credentials, 403 authenticated but not allowed, 404 not found (only after authorization passed), 409 conflict.
- Use the module logger (`logger = logging.getLogger(__name__)`); never `print`.

## Database and migrations
- Every table change ships with an Alembic migration in `app/alembic/versions/`. Create it with `.claude/scripts/dev.sh migration "<message>"`, write `upgrade()` and a working `downgrade()`, then run `.claude/scripts/dev.sh migrate`.
- Data migrations must preserve existing data (backfill before dropping a column).
- Store enum-like values as `VARCHAR` with a server default, not native PostgreSQL enums, so adding a value needs no migration.
- Never edit committed migrations (a hook enforces this).

## Tests (`backend/tests/`)
- Pytest with the fixtures in `tests/conftest.py`. Reuse `tests/utils/` helpers; extend them rather than duplicating login/user-creation code.
- Run with `.claude/scripts/dev.sh test` (or `dev.sh test tests/path::name -x` for a subset).
- The test session wipes the `user` table at the end; `dev.sh test` re-seeds automatically.

## After changing the API
Run `.claude/scripts/dev.sh client` so the frontend's generated types match.
