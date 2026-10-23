# Full Stack FastAPI Template — Claude Instructions

FastAPI + SQLModel + PostgreSQL backend (`backend/`), React + TypeScript + TanStack Router/Query frontend (`frontend/`), wired together with Docker Compose.

## Ground rules

- Read the scoped rules before touching code. They load automatically for matching paths, but read them explicitly when planning:
  - `.claude/rules/code-quality.md` — applies everywhere
  - `.claude/rules/backend.md` — `backend/**`
  - `.claude/rules/frontend.md` — `frontend/**`
  - `.claude/rules/rbac.md` — roles, permissions, authorization invariants
- Prefer clean, small, consistent changes over clever or broad ones. Match the surrounding code style.
- Never hand-edit generated files: `frontend/src/client/**`, `frontend/src/routeTree.gen.ts`, `backend/app/email-templates/**`. A hook blocks this. Regenerate instead.
- Never edit an Alembic migration that is already committed. Create a new one.
- Do not commit, push, or run `docker compose down -v` unless the user asks.

## Toolchain (Docker only — no local `uv`/`bun` required)

All commands go through one wrapper, run from the repo root:

| Command | What it does |
|---|---|
| `.claude/scripts/dev.sh up` | Build images, start db, mailpit, adminer, proxy, backend (:8000) and the Vite dev server (:5173) |
| `.claude/scripts/dev.sh be <cmd>` | Run a command in a one-off backend container with `./backend` mounted |
| `.claude/scripts/dev.sh fe <cmd>` | Run a command in the `frontend-dev` (Bun) container, in `/app/frontend` |
| `.claude/scripts/dev.sh migration "<msg>"` | Create an empty Alembic revision (prints its path) |
| `.claude/scripts/dev.sh seed` | Apply migrations + create initial data (`scripts/prestart.sh`) |
| `.claude/scripts/dev.sh test [pytest args]` | Run backend tests, then re-seed (tests wipe the `user` table) |
| `.claude/scripts/dev.sh format` | Ruff fix/format + Biome |
| `.claude/scripts/dev.sh lint` | mypy, ty, ruff (backend) + Biome (frontend) |
| `.claude/scripts/dev.sh client` | Regenerate the frontend OpenAPI client |
| `.claude/scripts/dev.sh typecheck` | Regenerate the route tree and type-check the frontend |
| `.claude/scripts/dev.sh check` | format → lint → test → typecheck |
| `.claude/scripts/dev.sh rebuild` | Rebuild the backend image and restart it so :8000 serves current code |

URLs: frontend dev <http://localhost:5173>, API <http://localhost:8000/docs>, Adminer <http://localhost:8080>, Mailpit <http://localhost:8025>.

## Skills

- `/add-rbac` — implements role-based access control (admin / manager / member) end-to-end: backend, migration, tests, frontend, docs. Idempotent: if RBAC already exists it verifies and repairs.
- `/add-role <name>` — adds a new role to an existing RBAC setup.

## Definition of done

Every change finishes with `.claude/scripts/dev.sh check` passing. For RBAC work, also walk `.claude/checklists/rbac-definition-of-done.md`.
