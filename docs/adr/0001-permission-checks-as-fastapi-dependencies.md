# ADR-0001: Permission checks as FastAPI dependencies over a central policy table

**Status:** Accepted, 2026-10-23

## Context

The template had a single boolean, `is_superuser`, checked in a dependency (`get_current_active_superuser`) and in a few handlers. We need three roles — admin, manager, member — protecting a small but realistic surface: listing and creating users, a metrics page, and profile management. Reviewers should be able to understand the whole authorization model in about five minutes, and adding a role must not mean editing a dozen files.

## Options considered

- **Inline role checks in handlers** (`if user.role == "admin"`): no new concepts, but checks get scattered, and every new role means auditing every route.
- **Custom decorators** (`@requires("admin")`): they read nicely but sit outside FastAPI's dependency injection, which hides them from OpenAPI and makes them awkward to combine with other dependencies.
- **ASGI middleware with a path-to-role table**: centralised, but it matches strings against URLs and can't see the loaded resource, so "owner or admin" checks still end up in handlers.
- **Policy engine** (Casbin, Oso): powerful, but it adds a dependency and a DSL to model three roles.
- **Permission enum + role→permission table + `require_permission` dependency**: chosen.

## Decision

`backend/app/core/rbac.py` defines `Role`, `Permission` (`resource:action`) and `ROLE_PERMISSIONS`, the only place that says which role can do what. Routes declare static requirements with `dependencies=[Depends(require_permission(Permission.X))]`. Checks that depend on the loaded resource ("yourself, or `users:read`"; "the item's owner, or `items:manage_all`") call `ensure_permission` / `has_permission` inside the handler. Both paths raise the same 403 and log the denial at WARNING. Code never compares role names, with one deliberate exception: an admin cannot delete themselves or change their own role, which prevents lock-out.

## Consequences

- **+** Adding a role means editing one dict. Adding a permission means adding an enum member and a `require_permission` call.
- **+** Each endpoint's requirement is visible in its decorator. The pattern is idiomatic FastAPI and easy to test with plain HTTP calls.
- **+** Error codes and denial logging are consistent everywhere.
- **−** There are no per-object ACLs. Ownership rules stay hand-written in the few handlers that need them.
- **−** The matrix is code, so changing who can do what needs a deploy rather than a database update. That's acceptable at this size, and changes get reviewed.
