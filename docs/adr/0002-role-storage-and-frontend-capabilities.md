# ADR-0002: Store the role as a column; send permissions to the frontend

**Status:** Accepted, 2026-10-23

## Context

Two related questions. Where does a user's role live? And how does the single-page app know what to show, without keeping its own copy of the permission matrix that can drift from the backend's?

## Options considered

**Role storage**

- **Native PostgreSQL enum**: strong typing in the database, but every new role needs an `ALTER TYPE` migration.
- **`roles` / `user_roles` / `permissions` tables**: supports many roles per user and runtime-editable policy, but adds joins, seed data and an admin UI that this scope doesn't need.
- **Role claim inside the JWT**: no database read, but a demoted user keeps their old rights until the token expires (8 days by default).
- **`VARCHAR(20)` column validated by a `Role` StrEnum**: chosen.

**Frontend capabilities**

- **Duplicate the matrix in TypeScript**: simple, but it silently drifts from the backend.
- **A separate `/permissions` endpoint**: one more request and one more cache to keep in sync.
- **Computed `permissions` on `UserPublic`, returned by `/users/me`**: chosen.

## Decision

`user.role` is a `VARCHAR(20)` column, `NOT NULL`, default `member`. The migration backfills `admin` from `is_superuser` before dropping that column. The `Role` enum validates values at the API boundary, and only admin-only endpoints accept the field. Because the role is read from the database on every request, a role change takes effect on the user's next request.

`UserPublic` exposes `role` (for display) and a computed, read-only `permissions` list derived from `ROLE_PERMISSIONS`. The generated TypeScript client types both, so `Permission` strings are checked at compile time. The UI decides visibility only through `usePermissions().can(...)` and `<RequirePermission>`, never from the role name. A forbidden page renders an "Access denied" view, and only a 401 logs the user out.

## Consequences

- **+** One source of truth for the policy, used by both enforcement (backend) and presentation (frontend).
- **+** A new role needs no migration and no frontend logic change, only a display label, which the compiler forces you to add.
- **+** Role changes apply immediately, with no stale token claims.
- **−** A user has exactly one role. Combining roles would need a different storage model.
- **−** The UI only notices a role change when it refetches `/users/me`. Until then, the backend's 403 is the safety net.
