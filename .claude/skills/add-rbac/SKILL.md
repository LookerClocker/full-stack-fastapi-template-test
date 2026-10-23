---
name: add-rbac
description: Implement role-based access control (admin / manager / member) end-to-end in this Full Stack FastAPI Template — permission policy, DB migration, guarded endpoints, metrics stub, seeded demo users, backend tests, permission-aware React UI with Access Denied states, README and ADRs. Use when asked to add RBAC, roles, permissions, or authorization to this project. Idempotent - on a project that already has RBAC it verifies and repairs instead.
argument-hint: "[optional: extra instructions]"
allowed-tools: Read, Edit, Write, Grep, Glob, Bash(.claude/scripts/dev.sh:*), Bash(.claude/skills/add-rbac/scripts/smoke_test.sh:*), Bash(git status:*), Bash(git diff:*), Bash(git switch -c:*), Bash(grep:*)
---

# Add RBAC

You are a senior Python + React engineer. Implement role-based access control in this repository **fully and autonomously**, following the phases below in order. Do not stop to ask questions unless a phase gate fails twice for a reason you cannot fix. Extra user instructions, if any: `$ARGUMENTS`.

Priorities, in order: **security correctness → clear, consistent code → focused tests → docs.** Keep scope tight.

## Rules you must follow (read them now, before Phase 0)

- `.claude/rules/rbac.md` — roles, **the permission matrix**, and the 7 invariants. This is the contract; everything below implements it.
- `.claude/rules/code-quality.md`
- `.claude/rules/backend.md`
- `.claude/rules/frontend.md`

The roles and permissions, inlined so they are never out of view:

| Permission | Grants | admin | manager | member |
|---|---|:-:|:-:|:-:|
| *(authenticated)* | Own profile, own password, own items | ✓ | ✓ | ✓ |
| `users:read` | List users, view any user | ✓ | ✓ | ✗ |
| `users:create` | Create users, choose their role | ✓ | ✗ | ✗ |
| `users:update` | Update any user, including role | ✓ | ✗ | ✗ |
| `users:delete` | Delete any user | ✓ | ✗ | ✗ |
| `metrics:read` | View metrics / insights | ✓ | ✓ | ✗ |
| `settings:manage` | Global settings (test email, email previews) | ✓ | ✗ | ✗ |
| `items:manage_all` | Read/edit/delete every user's items | ✓ | ✗ | ✗ |

Code checks **permissions**, never roles (one documented exception: admin lock-out). The matrix lives in exactly one place: `ROLE_PERMISSIONS` in `backend/app/core/rbac.py`.

## Tooling

All commands run through `.claude/scripts/dev.sh` (Docker only; see `CLAUDE.md`). Never call `uv`, `bun`, `pytest` or `alembic` directly on the host.

Blueprints with exact code live next to this file. Read each one at the start of its phase:
- `reference/backend.md` — Phases 1–4
- `reference/tests.md` — Phase 5
- `reference/frontend.md` — Phases 6–7
- `reference/docs.md` — Phase 8

Adapt blueprint code to the file as it actually is (imports, neighbours, formatting), but keep names, signatures, status codes and messages exactly as given so backend, frontend, tests and docs agree.

---

## Phase 0 — Preflight
1. Read the four rule files above.
2. `git status` — note pre-existing changes; never revert them. If on `master`/`main`, run `git switch -c feature/rbac`.
3. **Idempotency check:** if `backend/app/core/rbac.py` already exists, you are in *repair mode*: skip creation steps whose result already matches the blueprint, and go straight to verifying each checklist item, fixing only what is missing or wrong.
4. `.claude/scripts/dev.sh up` — stack must be healthy (db, backend :8000, frontend :5173).

**Gate:** `docker compose ps` shows `db` and `backend` healthy and `curl -s http://localhost:5173` responds.

## Phase 1 — Policy and model (backend)
Follow `reference/backend.md` §1–§3:
1. Create `backend/app/core/rbac.py` (Role, Permission, ROLE_PERMISSIONS, `permissions_for`, `has_permission`).
2. `backend/app/models.py`: replace `is_superuser` with `role`; add computed `permissions` to `UserPublic`; add `MetricsPublic`.
3. `backend/app/core/config.py`: add `DEMO_USER_PASSWORD`.
4. `backend/app/api/deps.py`: 401 for bad tokens, `ensure_permission`, `require_permission`, delete `get_current_active_superuser`.

## Phase 2 — Migration
Follow `reference/backend.md` §4:
1. `.claude/scripts/dev.sh migration "Replace is_superuser with role"` → note the printed file path.
2. Fill `upgrade()` / `downgrade()` exactly as the blueprint.
3. `.claude/scripts/dev.sh migrate`.

**Gate:** migrate succeeds; `.claude/scripts/dev.sh be python -c "from sqlmodel import Session, select; from app.core.db import engine; from app.models import User; print([(u.email, u.role) for u in Session(engine).exec(select(User))])"` shows `admin@example.com` as `admin`.

## Phase 3 — Endpoints
Follow `reference/backend.md` §5–§7: update `users.py`, `items.py`, `utils.py`, `login.py`; create `routes/metrics.py`; register it in `api/main.py`. Then `grep -rn "is_superuser\|get_current_active_superuser" backend/app --include=*.py | grep -v alembic/versions` must print nothing.

## Phase 4 — Seed demo users
Follow `reference/backend.md` §8: `init_db` seeds admin, plus manager + member in development only; set `DEMO_USER_PASSWORD` in `compose.override.yml` (never in `.env` or `compose.yml`). Run `.claude/scripts/dev.sh seed`.

## Phase 5 — Backend tests
Follow `reference/tests.md`: update fixtures/helpers, migrate existing tests off `is_superuser`, add `tests/api/routes/test_rbac.py`.

**Gate (loop until green):** `.claude/scripts/dev.sh format && .claude/scripts/dev.sh lint && .claude/scripts/dev.sh test`. Fix the code, not the test, when a security expectation fails.

## Phase 6 — Regenerate the API client
`.claude/scripts/dev.sh client`

**Gate:** `grep -n "export type Role\|export type Permission\|permissions:" frontend/src/client/types.gen.ts` finds all three, and `MetricsService` exists in `frontend/src/client/sdk.gen.ts`.

## Phase 7 — Frontend
Follow `reference/frontend.md` §1–§9: 401-only logout, roles/permissions primitives, Access Denied, sidebar, Users page, user forms, metrics page, settings, Playwright specs.

**Gate (loop until green):** `.claude/scripts/dev.sh format && .claude/scripts/dev.sh typecheck && .claude/scripts/dev.sh lint`, and `grep -rn "is_superuser" frontend/src frontend/tests --exclude-dir=client` prints nothing.

## Phase 8 — Documentation
Follow `reference/docs.md`: README RBAC section (quick start, demo accounts, matrix, approach, diagram, tests, migrations, extending) and two ADRs in `docs/adr/`.

## Phase 9 — Verify end-to-end
1. `.claude/scripts/dev.sh check` — must pass.
2. `.claude/scripts/dev.sh rebuild` — so :8000 serves the new backend.
3. `.claude/skills/add-rbac/scripts/smoke_test.sh` — logs in as admin, manager and member against the live API and asserts the matrix. Must print `ALL CHECKS PASSED`.
4. Walk `.claude/checklists/rbac-definition-of-done.md` box by box, verifying each against code or command output.

## Phase 10 — Report
Reply with:
- A short summary of what changed, grouped backend / frontend / docs, with file paths.
- The permission matrix.
- Demo credentials (`admin@example.com`, `manager@example.com`, `member@example.com` — passwords from `.env`) and URLs (http://localhost:5173, http://localhost:8000/docs).
- Results of `check` and the smoke test (pass counts), and any checklist box you could not verify, stated plainly.
- Do **not** commit. Offer to commit on the `feature/rbac` branch.
