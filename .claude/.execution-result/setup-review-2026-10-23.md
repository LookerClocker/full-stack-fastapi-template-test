# Developer setup review — 2026-10-23

**Question:** Does a developer need anything extra to set up this application after `/add-rbac`?

**Short answer:** For local development, mostly no. Docker is enough, and RBAC adds no new tools. There are some setup gaps, and **one deployment problem introduced by the RBAC change** (see the end of this file).

**Status:** ✅ fixed and verified on 2026-10-23 (see "Resolution" at the end). The deployment problem and the Node version pin are resolved; the docs are updated.

---

## What a new developer needs to know

### 1. Nothing is committed yet
All RBAC work (52 changed or new files) exists only locally, on branch `feature/rbac`. `master` is still at `b1125d8`. Anyone who clones the repo gets the original template until the work is committed and pushed.

### 2. Docker is the only requirement for the quick start
- The README quick start (build, prestart, `up`) sets up the migration and all three demo accounts.
- An existing database volume from before RBAC is handled automatically: `scripts/prestart.sh` runs migration `b6df181d0cf8`, which turns the old superuser into `admin`.

### 3. The Node version isn't pinned
- Vite 8 requires `"node": "^20.19.0 || >=22.12.0"` (from `node_modules/vite/package.json`).
- Nothing in the repo states this: there is no `.nvmrc` and no `engines` field in `frontend/package.json`. A developer on Node 16 or 18 hits the same failure seen on this machine.
- The docs assume Bun (`bun install`, `bun run dev`). Without Bun, `npx bun install` works, as used in this session.
- **Proposed:** add `.nvmrc` containing `22` and an `engines.node` field in `frontend/package.json`.

### 4. Running backend tests deletes all users
- The template's `tests/conftest.py` deletes every row in `user` and `item` at the end of the test session, including the demo accounts.
- `.claude/scripts/dev.sh test` re-seeds automatically, and the README explains it. Running `pytest` directly needs a manual re-seed afterwards.

### 5. Claude Code tooling prerequisites
- The hooks (`.claude/hooks/*.py`) need `python3`.
- `.claude/scripts/dev.sh` and `smoke_test.sh` need `bash`, `git` and `curl`. `smoke_test.sh` is written for bash 3.2, which macOS ships.
- macOS and Linux work as-is. Windows needs WSL or Git Bash.

### 6. `.idea/` is untracked
Keep it out of the commit, or add it to `.gitignore`.

### Already handled (no action needed)
| Item | Status |
|---|---|
| `frontend/openapi.json` | git-ignored (`frontend/.gitignore:14`) |
| Root `node_modules/` (from the host install on Node 22) | git-ignored (`.gitignore:3`) |
| `backend/app/frontend/` (build output) | git-ignored (`.gitignore:4`) |
| `.env` | tracked; it now contains `DEMO_USER_PASSWORD` (see the deployment problem below) |

---

## ⚠️ Deployment problem introduced by the RBAC change

**Cause:** `DEMO_USER_PASSWORD=changethis` was added to the committed `.env` and passed through `compose.yml` (`DEMO_USER_PASSWORD: ${DEMO_USER_PASSWORD:-}`). Neither deploy workflow overrides it. The workflows set `SECRET_KEY`, `FIRST_SUPERUSER_PASSWORD`, `POSTGRES_PASSWORD` and so on, but not `DEMO_USER_PASSWORD`.

| Deploy path | What happens |
|---|---|
| **Docker Compose** (`.github/workflows/deploy-docker-compose.yml`) | Compose reads `DEMO_USER_PASSWORD=changethis` from the checked-out `.env`. The deployed backend runs without `FASTAPI_ENV=development`, which is set only in `compose.override.yml`. `Settings._check_default_secret` therefore **raises a `ValueError`, and the backend fails to start.** |
| **FastAPI Cloud** (`.github/workflows/deploy.yml`) | The "Prepare database" step runs `uv run bash scripts/prestart.sh`. Settings load `../.env`, which also contains `FASTAPI_ENV=development`, so the check only warns. **`manager@example.com` and `member@example.com` get seeded in production with the password `changethis`.** |

Not caught earlier because the tests, smoke test and Playwright all run locally, where `FASTAPI_ENV=development` and the demo accounts are intended.

### Proposed fix (local setup unchanged)
1. Remove `DEMO_USER_PASSWORD` from `.env` and from `compose.yml`. Add it to `compose.override.yml` under the backend's `environment`, which only applies locally (deploys use `-f compose.yml -f compose.deploy.yml`).
2. In `init_db`, seed the demo accounts only when `settings.FASTAPI_ENV == "development"` **and** `DEMO_USER_PASSWORD` is set.
3. Update the README's "Demo accounts" note, and document the `uv` route: `DEMO_USER_PASSWORD=changethis uv run bash scripts/prestart.sh`.
4. Add a test proving that demo accounts are not seeded outside development.
5. Update the skill blueprint (`.claude/skills/add-rbac/reference/backend.md` §8) so future `/add-rbac` runs don't reintroduce the problem.

---

## Resolution (applied 2026-10-23)

### Changes
| File | Change |
|---|---|
| `.env` | Removed `DEMO_USER_PASSWORD`. The file is now identical to `master`. |
| `compose.yml` | Removed `DEMO_USER_PASSWORD`. The file is now identical to `master`. |
| `compose.override.yml` | Added `DEMO_USER_PASSWORD: ${DEMO_USER_PASSWORD:-changethis}` to the backend's `environment`. This file is local-only. |
| `backend/app/core/db.py` | Demo accounts are seeded only when `FASTAPI_ENV == "development"` **and** `DEMO_USER_PASSWORD` is set. |
| `backend/app/core/config.py` | Updated the comment on `DEMO_USER_PASSWORD`. |
| `backend/tests/crud/test_init_db.py` (new) | Tests that demo accounts are seeded in development and not seeded outside it. |
| `.claude/skills/add-rbac/scripts/smoke_test.sh` | Reads `DEMO_USER_PASSWORD` from the environment (default `changethis`) instead of `.env`. |
| `.nvmrc` (new) | `22` |
| `frontend/package.json` | `"engines": { "node": "^20.19.0 || >=22.12.0" }` (same range as Vite 8) |
| `README.md` | Quick start: Node requirement, `nvm use`, and options without Bun or Node. Demo accounts: development-only rule, why the password isn't in `.env`, and the `uv` command. Running tests: links `test_init_db.py`. |
| `development.md` | `.env` section: where the demo password lives, and the `uv` command. |
| `frontend/README.md` | Requirements: Node version and `.nvmrc`. |
| Skill and checklist | `add-rbac/SKILL.md` Phase 4, `reference/backend.md` §3 and §8, `reference/tests.md` §2b, `reference/docs.md`, `checklists/rbac-definition-of-done.md`. Future `/add-rbac` runs produce the fixed version. |

### Verification
| Check | Result |
|---|---|
| Backend format and lint (mypy, ty, ruff) | ✅ clean |
| Backend tests | ✅ **82 passed** (80 + 2 new `test_init_db` tests) |
| Backend rebuilt and re-seeded | ✅ healthy; admin, manager and member present locally |
| `smoke_test.sh` | ✅ 16/16 |
| Deploy config: `docker compose -f compose.yml -f compose.deploy.yml config` | ✅ renders (exit 0). The backend environment has **no `DEMO_USER_PASSWORD` and no `FASTAPI_ENV`**, so demo accounts can't be seeded and the default-secret check has nothing to reject. |
| Local config: `docker compose config` | ✅ `DEMO_USER_PASSWORD: changethis`, `FASTAPI_ENV: development` |
| FastAPI Cloud path | ✅ by inspection: the prestart step reads `.env`, which no longer contains `DEMO_USER_PASSWORD`, so demo accounts are not seeded |
| `nvm use` picks up `.nvmrc` | ✅ v22.23.4 |
| Frontend `tsc` (Node 22) | ✅ |
| Frontend Biome | ✅ 78 files clean (after removing git-ignored Playwright artifacts in `frontend/test-results/`; see note) |
| Playwright `admin.spec.ts` + `user-settings.spec.ts` | ✅ **27/27 passed** on clean data |

### Notes from verification
- **Docker Desktop hung:** its API returned `Internal Server Error`. A graceful quit and `docker desktop restart` were both ignored, so it was force-quit and reopened, with approval. The database volume was not affected.
- **Earlier Playwright failures** were environment and test-data issues, not code:
  - "Update password successfully" (flaky) and "Cancel edit action restores original email" (failed) ran during a manual backend restart. Both passed on the clean re-run.
  - "Edit a user successfully" failed once in strict mode because three users named "Updated Name" had built up from repeated runs on the same database. It passed once the database was reset by the backend test run.
- **Existing template behaviour:** Biome's `files.includes` doesn't exclude `frontend/test-results/`. After any local Playwright run, `biome check` reports `.last-run.json` until that folder is deleted. Not changed here (out of scope).
- **`dev.sh` limitation:** the frontend commands use the `frontend-dev` container, which publishes port 5173. While a dev server runs on the host (as now, on Node 22), `dev.sh fe|lint|typecheck|check` can't start that container. The frontend checks above were run on the host with Node 22 instead.

---

## Follow-up: manager test coverage (2026-10-23)

### Added
**Backend: `backend/tests/api/routes/test_rbac.py`, 5 tests**
| Test | Checks |
|---|---|
| `test_manager_cannot_send_test_email` | `POST /utils/test-email/` → 403 |
| `test_manager_cannot_preview_recovery_email` | `POST /password-recovery-html-content/{email}` → 403 |
| `test_manager_cannot_access_other_users_items` | read, update and delete another user's item → 403 each |
| `test_manager_sees_only_own_items` | `GET /items/` returns only the manager's items |
| `test_admin_can_access_any_item` | admin reads another user's item → 200 (the allowed side) |

**Frontend: `frontend/tests/rbac.spec.ts`, 5 Playwright tests, plus the helper `frontend/tests/utils/adminApi.ts`**
| Test | Checks |
|---|---|
| Manager › sees Users and Metrics in the sidebar | both links visible |
| Manager › has a read-only users page | rows visible, no "Add User", no buttons in table rows |
| Manager › can open the metrics page | heading and "Total users" card visible |
| Member › sees neither Users nor Metrics in the sidebar | links absent, Items present |
| Member › opening /metrics directly shows access denied and stays logged in | `access-denied` visible, URL still `/metrics` |

### Verification
| Check | Result |
|---|---|
| Mutation check: manager temporarily given `settings:manage` + `items:manage_all` | ✅ all 4 new denial tests **failed** as expected (the 5th checks the allowed side); `rbac.py` restored and diff-checked |
| `test_rbac.py` | ✅ 27 passed |
| Full backend suite | ✅ **87 passed** (82 + 5) |
| Backend lint (mypy, ty, ruff) | ✅ clean |
| Frontend `tsc` and Biome (Node 22) | ✅ clean (80 files) |
| **Full Playwright suite** (all specs, rebuilt image) | ✅ **66 passed, 1 flaky.** All 5 new RBAC tests passed on the first try. |

**Flaky test:** `reset-password.spec.ts` › "User can reset password successfully using the link" failed once with `Timeout while trying to get the latest email` from Mailpit, then passed on retry. It's a public flow with no role checks, so it's unrelated to RBAC. The likely cause is email delivery lagging under the parallel run.

**Docs and skill updated:** README "Running tests" section; `.claude/skills/add-rbac/reference/tests.md` (manager tests); `reference/frontend.md` §9 (`adminApi.ts`, `rbac.spec.ts`, the settings-spec change); checklist.
