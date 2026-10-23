# RBAC — Definition of Done

Walk every box. Verify each one against the code or a command output, not memory. Report any box you could not check.

## Backend — model and policy
- [ ] `backend/app/core/rbac.py` holds `Role`, `Permission`, `ROLE_PERMISSIONS`, `permissions_for`, `has_permission` and imports nothing from FastAPI or the DB.
- [ ] `User.role` exists (`VARCHAR(20)`, default `member`); `is_superuser` is gone from models, routes, crud, tests and frontend (`grep -rn is_superuser backend/app backend/tests frontend/src frontend/tests --exclude-dir=client` only hits old migrations).
- [ ] `UserPublic` exposes `role` and computed `permissions`.
- [ ] `UserRegister` and `UserUpdateMe` have no `role` field.

## Backend — migration and seed
- [ ] New Alembic migration adds `role`, backfills `admin` from `is_superuser`, drops `is_superuser`, and has a working `downgrade()`.
- [ ] `.claude/scripts/dev.sh migrate` succeeds on the existing database.
- [ ] `init_db` creates the first superuser as `admin`, plus `manager@example.com` and `member@example.com` only when `FASTAPI_ENV == "development"` and `DEMO_USER_PASSWORD` is set. Re-running is idempotent.
- [ ] `DEMO_USER_PASSWORD` is set only in `compose.override.yml`; `grep -n DEMO_USER_PASSWORD .env compose.yml` prints nothing.
- [ ] `tests/crud/test_init_db.py` proves demo accounts are not seeded outside development.

## Backend — enforcement
- [ ] `deps.py` has `require_permission` (dependency factory) and `ensure_permission` (in-handler), both logging denials at WARNING.
- [ ] `get_current_active_superuser` no longer exists; nothing references it.
- [ ] Invalid/missing token → 401 with `WWW-Authenticate: Bearer`.
- [ ] Every route matches the matrix in `.claude/rules/rbac.md` (users list/read/create/update/delete, metrics, test-email, password-recovery-html-content, items ownership).
- [ ] `GET /api/v1/metrics/` exists and requires `metrics:read`.
- [ ] Admin cannot change own role (403) or delete self (403).
- [ ] Signup with `"role": "admin"` yields a `member`. `PATCH /users/me` with `"role"` is ignored.

## Backend — tests
- [ ] `backend/tests/api/routes/test_rbac.py` covers allowed **and** denied paths for each role on: list users, create user, metrics, own profile, update another user; plus self-escalation and unauthenticated 401.
- [ ] Manager is tested as denied on settings endpoints and other users' items (`test_manager_*` in `test_rbac.py`).
- [ ] Existing tests updated for `role`, all green: `.claude/scripts/dev.sh test`.

## Frontend
- [ ] Client regenerated (`.claude/scripts/dev.sh client`); `Role`, `Permission`, `MetricsPublic`, `MetricsService` exist in `src/client`.
- [ ] `src/main.tsx` logs out only on 401.
- [ ] `src/hooks/usePermissions.ts`, `src/components/Common/RequirePermission.tsx`, `src/components/Common/AccessDenied.tsx`, `src/lib/roles.ts` exist.
- [ ] Sidebar items declare a `permission` and are filtered with `can()`; no `is_superuser`/role checks remain.
- [ ] `/admin` (Users) gated by `users:read`; Add User by `users:create`; row actions by `users:update` / `users:delete`.
- [ ] `/metrics` page exists, gated by `metrics:read`, with a sidebar link.
- [ ] Add/Edit user forms use a role `Select` fed by `ROLE_LABELS`; the users table shows a role badge.
- [ ] Navigating directly to a forbidden page shows "Access denied" (no redirect, no logout).
- [ ] Settings hides "Danger zone" for admins (mirrors backend rule).
- [ ] Playwright specs that referenced "Is superuser?" are updated; `tests/rbac.spec.ts` covers the manager (links, read-only Users, Metrics) and member (no links, Access denied) views.
- [ ] `.claude/scripts/dev.sh typecheck` passes.
- [ ] `.nvmrc` pins Node 22 and `frontend/package.json` has `engines.node` `^20.19.0 || >=22.12.0`.

## Docs
- [ ] README has an RBAC section: quick start, demo accounts, permission matrix, approach (2–4 paragraphs), Mermaid diagram, tests, migrations, how to add a role.
- [ ] `docs/adr/0001-*.md` and `docs/adr/0002-*.md` exist (200–400 words each).

## Final verification
- [ ] `.claude/scripts/dev.sh check` passes.
- [ ] `.claude/scripts/dev.sh rebuild` then `.claude/skills/add-rbac/scripts/smoke_test.sh` passes against the running stack.
