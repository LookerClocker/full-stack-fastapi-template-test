---
paths:
  - "frontend/**"
---

# Frontend Rules (React / TypeScript / TanStack)

## Stack
React 19, TypeScript (strict), TanStack Router (file routes in `src/routes/`), TanStack Query, react-hook-form + zod, Tailwind, shadcn/ui primitives in `src/components/ui/`, Biome for lint/format.

## Layout
| Path | Holds |
|---|---|
| `src/client/` | **Generated** OpenAPI client. Never edit — run `.claude/scripts/dev.sh client`. |
| `src/routes/` | One file per page. `_layout/*` pages are behind login. `routeTree.gen.ts` is generated. |
| `src/components/<Feature>/` | Feature components (`Admin/`, `Items/`, `UserSettings/`). |
| `src/components/Common/` | Shared app-level components (errors, layout pieces, guards). |
| `src/components/ui/` | shadcn/ui primitives. Do not modify for feature needs; compose them. |
| `src/hooks/` | Reusable hooks (`useAuth`, `usePermissions`). |
| `src/lib/` | Pure helpers and constants (`roles.ts`). |

## Conventions
- Types come from the generated client (`import type { UserPublic, Permission } from "@/client"`). Never re-declare API shapes by hand.
- Data fetching through TanStack Query with stable `queryKey`s; call the generated `*Service` methods.
- Forms: react-hook-form + zod schema at the top of the component file, shadcn `Form*` components.
- Use existing primitives (`Button`, `Card`, `Select`, `Badge`, `Dialog`) before writing new markup.
- Add `data-testid` to new top-level states (e.g. `access-denied`) so Playwright can target them.
- Path alias `@/` → `src/`. Named exports for new components unless the folder already uses default exports.
- No `any`. No non-null assertions on API data.

## Authorization in the UI
- The UI hides what the user cannot do; the backend enforces it. Never rely on the UI for security.
- Decide visibility from `user.permissions` via `usePermissions().can(...)` or `<RequirePermission>` — never from `user.role` (role is display-only). Sole exception: hiding "Danger zone" for admins, mirroring the backend lock-out rule.
- Unauthorized direct navigation renders `<AccessDenied />`, never a blank page, a silent redirect, or a logout.
- Only HTTP 401 logs the user out. 403 is "not allowed", not "not logged in".

## Checks
`.claude/scripts/dev.sh format` then `.claude/scripts/dev.sh typecheck`. The dev server at http://localhost:5173 hot-reloads from the host files.
