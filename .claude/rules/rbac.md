---
paths:
  - "backend/app/**"
  - "backend/tests/**"
  - "frontend/src/**"
  - "README.md"
  - "docs/**"
---

# RBAC Rules — roles, permissions, invariants

## Model
- **Roles are bundles of permissions. Code checks permissions, never roles.** The only place that knows which role can do what is `ROLE_PERMISSIONS` in `backend/app/core/rbac.py`.
- Roles: `admin`, `manager`, `member` (`Role` StrEnum). Permissions: `resource:action` strings (`Permission` StrEnum).
- A user has exactly one role, stored as `user.role` (`VARCHAR(20)`, default `member`).
- The API exposes `role` and the derived `permissions` list on `UserPublic`. The frontend reads `permissions`.

## Permission matrix (source of truth: `ROLE_PERMISSIONS`)
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

## Invariants — never break these
1. **Deny by default.** Every endpoint is either public on purpose (login, signup, password recovery, health check), authenticated-only (own resources), or guarded by `require_permission(...)`. No fourth option.
2. **No self-escalation.** `role` is settable only through `POST /users/` and `PATCH /users/{id}`, both admin-only. `UserRegister`, `UserUpdateMe` and the dev-only private endpoint never accept it; signup always yields `member`.
3. **No lock-out.** An admin cannot change their own role or delete their own account.
4. **Correct status codes.** 401 = no/invalid token (with `WWW-Authenticate: Bearer`). 403 = valid user lacking permission. Authorization runs before existence checks, so 404 never leaks whether a forbidden resource exists.
5. **Observable denials.** Every 403 from the permission layer logs a `WARNING` with user id, role, and the missing permission. No emails or tokens in logs.
6. **One enforcement point per check.** Static checks use `require_permission` in the route decorator; resource-dependent checks call `ensure_permission` (or `has_permission` for ownership-or-permission logic) in the handler. Do not hand-roll `if user.role == ...` — the single exception is the admin lock-out guard of invariant 3, which is about the role itself.
7. **UI mirrors, backend enforces.** Frontend gates use the same permission names; hiding a button is UX, not security.

## Extending
Adding a role or permission touches: `backend/app/core/rbac.py` (enum + matrix), `frontend/src/lib/roles.ts` (label — the compiler forces this), the README matrix, and `backend/tests/api/routes/test_rbac.py`. Then `.claude/scripts/dev.sh client`. No migration needed for a new role. Use `/add-role`.
