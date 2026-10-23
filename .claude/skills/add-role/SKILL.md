---
name: add-role
description: Add a new role (or a new permission) to this project's existing RBAC setup - policy table, frontend label, tests and README matrix - without a database migration. Use when asked to add a role like "auditor" or "support", or to grant/revoke a permission for a role. Requires /add-rbac to have been applied.
argument-hint: "<role-name> [permissions it should hold, e.g. users:read metrics:read]"
allowed-tools: Read, Edit, Write, Grep, Glob, Bash(.claude/scripts/dev.sh:*), Bash(.claude/skills/add-rbac/scripts/smoke_test.sh:*), Bash(git status:*), Bash(git diff:*)
---

# Add a role

Request: `$ARGUMENTS`

Read `.claude/rules/rbac.md` and `.claude/rules/code-quality.md` first. If `backend/app/core/rbac.py` does not exist, stop and tell the user to run `/add-rbac` first.

If the request doesn't say which permissions the role holds, pick the least-privileged set that fits the role's name, and state your choice in the report. Never grant `users:create`, `users:update` or `users:delete` without the user explicitly asking — those allow privilege escalation.

## Steps

1. **Policy** — `backend/app/core/rbac.py`: add the member to `Role` (lowercase value), and its entry in `ROLE_PERMISSIONS`. If a new permission is needed, add it to `Permission` as `resource:action` and guard the endpoint with `require_permission` (see `.claude/skills/add-rbac/reference/backend.md` §3).
2. **No migration** — `user.role` is `VARCHAR(20)`; confirm the new value is ≤ 20 characters.
3. **Client** — `.claude/scripts/dev.sh client`.
4. **Frontend** — add the label to `ROLE_LABELS` in `frontend/src/lib/roles.ts` (`dev.sh typecheck` fails until you do). For a new permission, gate the relevant nav item/page/button with that permission string.
5. **Tests** — in `backend/tests/api/routes/test_rbac.py`: add a token fixture for the role in `tests/conftest.py` (copy the `manager_token_headers` pattern), map it in `TOKEN_FIXTURE_BY_ROLE`, and add `ACCESS_MATRIX` rows for the role on `/users/`, `/metrics/` and `/users/me`.
6. **Docs** — add the column to both permission tables in `README.md` and to the matrix in `.claude/rules/rbac.md` and `.claude/skills/add-rbac/SKILL.md`.
7. **Verify** — `.claude/scripts/dev.sh check`, then `.claude/scripts/dev.sh rebuild`.

Report: files changed, the role's permissions, and check results. Do not commit.
