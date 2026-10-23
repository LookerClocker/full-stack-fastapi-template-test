# Documentation blueprint

Write for a reviewer who wants to run the project and understand the authorization model in five minutes. Concise, concrete, no marketing. Every claim must match the code you just wrote — re-read `backend/app/core/rbac.py` before writing the matrix.

## §1 `README.md` — new section

Insert a `## Role-Based Access Control (RBAC)` section directly **after the intro paragraph and before `## Technology Stack and Features`**. Use these subsections, in order:

### Quick start
Numbered steps that work on a fresh clone with only Docker installed:
1. `docker compose build backend`
2. `docker compose run --rm backend bash scripts/prestart.sh` — runs migrations and seeds the three accounts.
3. `docker compose up -d --wait backend`
4. Open <http://localhost:8000> (built frontend) or <http://localhost:8000/docs>.
5. Frontend dev server (hot reload): `bun install && bun run dev` → <http://localhost:5173>. Mention the Docker-only alternative: `.claude/scripts/dev.sh up`.

### Demo accounts
Table: email, role, password source. `admin@example.com` (`FIRST_SUPERUSER_PASSWORD` in `.env`), `manager@example.com` and `member@example.com` (`DEMO_USER_PASSWORD`, default `changethis`, set in `compose.override.yml`). State that demo accounts are seeded only when `FASTAPI_ENV=development` and `DEMO_USER_PASSWORD` is set, that the password is deliberately kept out of the tracked `.env` so no deploy path picks it up, and the `uv` form: `DEMO_USER_PASSWORD=changethis uv run bash scripts/prestart.sh`. To re-seed: re-run step 2 (idempotent). In the quick start, state the Node requirement (`^20.19 || >=22.12`, `.nvmrc` pins 22).

### Permission matrix
Two tables:
1. **Actions × roles** (the reviewer-facing view): List all users; View any user; Create user; Update any user / change role; Delete user; View metrics; Global settings (test email); Manage everyone's items; View/update own profile; Manage own items; Delete own account (✗ for admin — lock-out protection).
2. **Endpoint → permission** mapping: `GET /users/` users:read, `GET /users/{id}` self or users:read, `POST /users/` users:create, `PATCH /users/{id}` users:update, `DELETE /users/{id}` users:delete, `GET /metrics/` metrics:read, `POST /utils/test-email/` and `POST /password-recovery-html-content/{email}` settings:manage, `/items/*` owner or items:manage_all, `/users/me*` authenticated.

### How authorization works
2–4 short paragraphs covering exactly:
- **Where checks live:** FastAPI dependencies, not middleware or decorators. `require_permission(Permission.X)` in the route decorator for static checks; `ensure_permission(user, X)` inside a handler only when the answer depends on the loaded resource (self-or-permission, ownership). Both raise 403 and log a WARNING with user id, role and permission. Invalid/missing tokens are 401.
- **How roles are stored and validated:** `user.role` VARCHAR(20) column, default `member`, validated by the `Role` StrEnum at the API boundary. Roles map to permissions in one dict, `ROLE_PERMISSIONS` in `backend/app/core/rbac.py`. Code checks permissions, never roles. Role can only be set by an admin (`POST /users/`, `PATCH /users/{id}`); signup and profile updates can't carry it; admins can't change their own role or delete themselves.
- **How the frontend learns capabilities:** `GET /users/me` returns `role` and a computed `permissions` list. `usePermissions().can()` and `<RequirePermission>` hide nav links and buttons; direct navigation to a forbidden page renders an "Access denied" view. Only 401 logs the user out. The UI is convenience; the backend is the enforcement.

### Request flow diagram
A Mermaid `flowchart LR`: Browser → (JWT) → FastAPI route → `get_current_user` (401 on bad token) → `require_permission` / `ensure_permission` (403 + WARNING log) → `ROLE_PERMISSIONS` lookup → handler → DB. A second small branch: `GET /users/me` → `permissions[]` → `usePermissions` → sidebar / RequirePermission / AccessDenied.

### Running tests
- Backend: `docker compose exec backend bash scripts/tests-start.sh` needs the source synced (`docker compose watch`), so document the reliable form: `.claude/scripts/dev.sh test`, or with uv: `cd backend && uv run bash scripts/test.sh`. Point to `backend/tests/api/routes/test_rbac.py` as the authorization suite and list what it covers in one line.
- Note: the test session deletes all users at the end; re-run the seed step afterwards (`dev.sh test` does it automatically).
- Frontend E2E (optional): `bunx playwright test` with the stack running.

### Database migration
One paragraph: migration `<revision id>` adds `user.role`, backfills `admin` from `is_superuser`, then drops `is_superuser`; it is reversible (`alembic downgrade -1`). Applied automatically by `scripts/prestart.sh`.

### Adding a role or permission
Numbered: (1) add to `Role`/`Permission` and `ROLE_PERMISSIONS` in `backend/app/core/rbac.py`; (2) add the label in `frontend/src/lib/roles.ts` (TypeScript errors until you do); (3) guard endpoints with `require_permission`; (4) regenerate the client; (5) add rows to `test_rbac.py` and this matrix. No DB migration for a new role. Mention the `/add-role` Claude skill.

## §2 ADRs — `docs/adr/` (create the folder)

Format for each (200–400 words): `# ADR-000N: <title>`, then **Status** (Accepted, <today's date>), **Context**, **Options considered** (bulleted, one line each with its main drawback), **Decision**, **Consequences** (positive and negative).

`docs/adr/0001-permission-checks-as-fastapi-dependencies.md`
- Context: template had a binary `is_superuser`; need 3 roles with a small, auditable surface; reviewers must grasp it fast.
- Options: inline `if user.role == ...` in handlers (scattered, role-coupled); custom decorators (fight FastAPI's DI, hide deps from OpenAPI); ASGI middleware with a path→role table (string matching, no access to loaded resources); policy engines like Casbin/Oso (new dependency and DSL for 3 roles); **permission enum + role→permission table + `require_permission` dependency** (chosen).
- Decision and why: native FastAPI pattern, visible in route signatures, testable, one table to audit; resource-dependent checks via `ensure_permission`.
- Consequences: + adding a role edits one dict; + consistent 403 + logging. − no per-object ACLs (ownership stays hand-written in handlers); − the matrix is code, so changing it needs a deploy.

`docs/adr/0002-role-storage-and-frontend-capabilities.md`
- Context: where to store the role, and how the SPA knows what to show without duplicating the matrix.
- Storage options: native PG enum (migration per new role); roles/permissions tables (overkill, more joins and admin UI); role claim in JWT (stale after role change until expiry); **VARCHAR column validated by `Role` StrEnum** (chosen; one role per user).
- Frontend options: duplicate the matrix in TS (drifts); separate `/permissions` endpoint (extra request); **computed `permissions` on `UserPublic` from `/users/me`** (chosen; same source of truth, typed via the generated client).
- Consequences: + role change takes effect on the next request; + UI never decides from role names. − one role per user; − UI only refreshes permissions when `currentUser` is refetched.
