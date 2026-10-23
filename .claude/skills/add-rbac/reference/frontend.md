# Frontend blueprint

Paths relative to `frontend/`. Prerequisite: Phase 6 regenerated `src/client` so `Role`, `Permission`, `UserPublic.permissions`, `MetricsPublic` and `MetricsService` exist. If an import below doesn't resolve, re-run `.claude/scripts/dev.sh client` — never hand-write API types.

The principle: **UI checks permissions from `user.permissions`; the backend enforces.** Forbidden pages render `<AccessDenied />`, they don't redirect or log out.

## §1 `src/main.tsx` — only 401 means "logged out"
In `handleApiError`, replace `[401, 403].includes(error.response?.status ?? 0)` with `error.response?.status === 401`. Otherwise a manager who hits a 403 would be logged out.

## §2 `src/lib/roles.ts` (new) — display labels; the compiler forces a label for every backend role
```ts
import type { Role } from "@/client"

export const ROLE_LABELS: Record<Role, string> = {
  admin: "Admin",
  manager: "Manager",
  member: "Member",
}

export const ROLES = Object.keys(ROLE_LABELS) as Role[]
```

## §3 `src/hooks/usePermissions.ts` (new)
```ts
import type { Permission } from "@/client"
import useAuth from "./useAuth"

export function usePermissions() {
  const { user } = useAuth()

  const can = (permission: Permission) =>
    user?.permissions.includes(permission) ?? false

  return { can, isLoaded: user != null }
}
```

## §4 Guard + Access Denied components (new)

`src/components/Common/RequirePermission.tsx`:
```tsx
import type { ReactNode } from "react"

import type { Permission } from "@/client"
import { usePermissions } from "@/hooks/usePermissions"

interface RequirePermissionProps {
  permission: Permission
  children: ReactNode
  fallback?: ReactNode
}

export function RequirePermission({
  permission,
  children,
  fallback = null,
}: RequirePermissionProps) {
  const { can, isLoaded } = usePermissions()

  if (!isLoaded) {
    return null
  }
  return can(permission) ? children : fallback
}
```

`src/components/Common/AccessDenied.tsx`:
```tsx
import { Link } from "@tanstack/react-router"
import { ShieldX } from "lucide-react"

import { Button } from "@/components/ui/button"

export function AccessDenied() {
  return (
    <div
      className="flex flex-col items-center justify-center gap-4 py-24 text-center"
      data-testid="access-denied"
    >
      <ShieldX className="size-12 text-muted-foreground" />
      <h1 className="text-2xl font-bold tracking-tight">Access denied</h1>
      <p className="max-w-md text-muted-foreground">
        You don't have permission to view this page. If you need access, ask an
        administrator to change your role.
      </p>
      <Button asChild>
        <Link to="/">Back to dashboard</Link>
      </Button>
    </div>
  )
}
```

## §5 Sidebar — `src/components/Sidebar/AppSidebar.tsx`
Each nav entry declares the permission it needs; filter with `can()`. Remove the `is_superuser` branch.
```tsx
import { Briefcase, ChartColumn, Home, Users } from "lucide-react"
import type { Permission } from "@/client"
import { usePermissions } from "@/hooks/usePermissions"

type NavItem = Item & { permission?: Permission }

const navItems: NavItem[] = [
  { icon: Home, title: "Dashboard", path: "/" },
  { icon: Briefcase, title: "Items", path: "/items" },
  { icon: Users, title: "Users", path: "/admin", permission: "users:read" },
  { icon: ChartColumn, title: "Metrics", path: "/metrics", permission: "metrics:read" },
]

// inside AppSidebar():
const { can } = usePermissions()
const items = navItems.filter((item) => !item.permission || can(item.permission))
```
Keep `useAuth()` for the footer `<User user={currentUser} />`.

## §6 Users page — `src/routes/_layout/admin.tsx`
- **Remove** the `beforeLoad` redirect (it was a silent redirect; now direct navigation shows Access Denied).
- Wrap the page so the users query never fires without permission, and gate the Add button:
```tsx
function Admin() {
  return (
    <RequirePermission permission="users:read" fallback={<AccessDenied />}>
      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Users</h1>
            <p className="text-muted-foreground">
              Manage user accounts and permissions
            </p>
          </div>
          <RequirePermission permission="users:create">
            <AddUser />
          </RequirePermission>
        </div>
        <UsersTable />
      </div>
    </RequirePermission>
  )
}
```
Change the `head` title to `"Users - FastAPI Template"`.

`src/components/Admin/UserActionsMenu.tsx` — show each action only with its permission; render nothing if neither is allowed:
```tsx
const { can } = usePermissions()
const canEdit = can("users:update")
const canDelete = can("users:delete")

if (user.id === currentUser?.id || (!canEdit && !canDelete)) {
  return null
}
// in DropdownMenuContent:
{canEdit && <EditUser user={user} onSuccess={() => setOpen(false)} />}
{canDelete && <DeleteUser id={user.id} onSuccess={() => setOpen(false)} />}
```

`src/components/Admin/columns.tsx` — the "Role" column: `accessorKey: "role"`, badge text `ROLE_LABELS[row.original.role]`, variant `row.original.role === "admin" ? "default" : "secondary"` (display only).

## §7 Role selection in user forms

`src/components/Admin/RoleSelect.tsx` (new):
```tsx
import type { Role } from "@/client"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ROLE_LABELS, ROLES } from "@/lib/roles"

interface RoleSelectProps {
  value: Role
  onChange: (role: Role) => void
}

export function RoleSelect({ value, onChange }: RoleSelectProps) {
  return (
    <Select value={value} onValueChange={(role) => onChange(role as Role)}>
      <SelectTrigger className="w-full" aria-label="Role">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {ROLES.map((role) => (
          <SelectItem key={role} value={role}>
            {ROLE_LABELS[role]}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
```

`AddUser.tsx` and `EditUser.tsx`:
- zod: replace `is_superuser: z.boolean()` / `.optional()` with `role: z.enum(ROLES as [Role, ...Role[]])` (AddUser) and `role: z.enum(ROLES as [Role, ...Role[]]).optional()` (EditUser).
- defaults: AddUser `role: "member"`; EditUser `role: user.role`.
- Replace the "Is superuser?" checkbox `FormField` with:
```tsx
<FormField
  control={form.control}
  name="role"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Role</FormLabel>
      <FormControl>
        <RoleSelect value={field.value ?? "member"} onChange={field.onChange} />
      </FormControl>
      <FormMessage />
    </FormItem>
  )}
/>
```
Keep the "Is active?" checkbox. Remove now-unused imports.

## §8 Metrics page — `src/routes/_layout/metrics.tsx` (new)
```tsx
import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Suspense } from "react"

import { MetricsService } from "@/client"
import { AccessDenied } from "@/components/Common/AccessDenied"
import { RequirePermission } from "@/components/Common/RequirePermission"
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { ROLE_LABELS, ROLES } from "@/lib/roles"

export const Route = createFileRoute("/_layout/metrics")({
  component: Metrics,
  head: () => ({
    meta: [{ title: "Metrics - FastAPI Template" }],
  }),
})

function MetricCard({ title, value }: { title: string; value: number }) {
  return (
    <Card>
      <CardHeader>
        <CardDescription>{title}</CardDescription>
        <CardTitle className="text-3xl tabular-nums">{value}</CardTitle>
      </CardHeader>
    </Card>
  )
}

function MetricsGrid() {
  const { data: metrics } = useSuspenseQuery({
    queryKey: ["metrics"],
    queryFn: async () => (await MetricsService.readMetrics()).data,
  })

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <MetricCard title="Total users" value={metrics.total_users} />
      <MetricCard title="Active users" value={metrics.active_users} />
      <MetricCard title="Total items" value={metrics.total_items} />
      {ROLES.map((role) => (
        <MetricCard
          key={role}
          title={`${ROLE_LABELS[role]} accounts`}
          value={metrics.users_by_role[role] ?? 0}
        />
      ))}
    </div>
  )
}

function Metrics() {
  return (
    <RequirePermission permission="metrics:read" fallback={<AccessDenied />}>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Metrics</h1>
          <p className="text-muted-foreground">
            A snapshot of users and items across the app
          </p>
        </div>
        <Suspense fallback={<Skeleton className="h-32 w-full" />}>
          <MetricsGrid />
        </Suspense>
      </div>
    </RequirePermission>
  )
}
```
`routeTree.gen.ts` regenerates automatically (dev server / `dev.sh typecheck`); never edit it.

## §9 Settings and Playwright

`src/routes/_layout/settings.tsx` — admins cannot delete their own account (backend rule), so hide that tab for them. Replace the `is_superuser` ternary (which also had an off-by-one `slice(0, 3)` that hid nothing):
```tsx
const finalTabs =
  currentUser?.role === "admin"
    ? tabsConfig.filter((tab) => tab.value !== "danger-zone")
    : tabsConfig
```

`tests/admin.spec.ts` (Playwright, run separately — not part of the gate):
- "Create a superuser": replace `page.getByLabel("Is superuser?").check()` with
  `await page.getByRole("combobox", { name: "Role" }).click()` then `await page.getByRole("option", { name: "Admin" }).click()`; rename the test to "Create an admin user"; assert the row shows "Admin" instead of "Superuser".
- "Non-superuser cannot access admin page" → "Member sees access denied on users page": after `page.goto("/admin")`, `await expect(page.getByTestId("access-denied")).toBeVisible()`.
- Rename remaining "superuser" wording to "admin". Anything else asserting the "Superuser" badge now expects "Admin".

`tests/user-settings.spec.ts`: the default (admin) session must **not** see the "Danger zone" tab — replace the "All tabs are visible" test accordingly.

New `tests/utils/adminApi.ts` (only admins can assign roles):
```ts
import { LoginService, type Role, UsersService } from "../../src/client"
import { client } from "../../src/client/client.gen"
import { firstSuperuser, firstSuperuserPassword } from "../config.ts"

client.setConfig({
  baseURL: `${process.env.VITE_API_URL}`,
})

// Only admins may assign roles, so log in as the first superuser to create the user.
export const createUserWithRole = async ({
  email,
  password,
  role,
}: {
  email: string
  password: string
  role: Role
}) => {
  const { data: token } = await LoginService.loginAccessToken({
    body: { username: firstSuperuser, password: firstSuperuserPassword },
  })
  const response = await UsersService.createUser({
    body: { email, password, role, is_active: true },
    headers: { Authorization: `Bearer ${token.access_token}` },
  })
  return response.data
}
```

New `tests/rbac.spec.ts` — the manager and member views:
```ts
import { expect, type Page, test } from "@playwright/test"
import { createUserWithRole } from "./utils/adminApi"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test.use({ storageState: { cookies: [], origins: [] } })

const sidebarLink = (page: Page, name: string) =>
  page.getByRole("link", { name, exact: true })

test.describe("Manager", () => {
  const email = randomEmail()
  const password = randomPassword()

  test.beforeAll(async () => {
    await createUserWithRole({ email, password, role: "manager" })
  })

  test.beforeEach(async ({ page }) => {
    await logInUser(page, email, password)
  })

  test("sees Users and Metrics in the sidebar", async ({ page }) => {
    await expect(sidebarLink(page, "Users")).toBeVisible()
    await expect(sidebarLink(page, "Metrics")).toBeVisible()
  })

  test("has a read-only users page", async ({ page }) => {
    await page.goto("/admin")

    await expect(page.getByRole("row").filter({ hasText: email })).toBeVisible()
    await expect(page.getByRole("button", { name: "Add User" })).toHaveCount(0)
    await expect(page.locator("tbody").getByRole("button")).toHaveCount(0)
  })

  test("can open the metrics page", async ({ page }) => {
    await page.goto("/metrics")

    await expect(page.getByRole("heading", { name: "Metrics" })).toBeVisible()
    await expect(page.getByText("Total users")).toBeVisible()
  })
})

test.describe("Member", () => {
  const email = randomEmail()
  const password = randomPassword()

  test.beforeAll(async () => {
    await createUser({ email, password })
  })

  test.beforeEach(async ({ page }) => {
    await logInUser(page, email, password)
  })

  test("sees neither Users nor Metrics in the sidebar", async ({ page }) => {
    await expect(sidebarLink(page, "Items")).toBeVisible()
    await expect(sidebarLink(page, "Users")).toHaveCount(0)
    await expect(sidebarLink(page, "Metrics")).toHaveCount(0)
  })

  test("opening /metrics directly shows access denied and stays logged in", async ({
    page,
  }) => {
    await page.goto("/metrics")

    await expect(page.getByTestId("access-denied")).toBeVisible()
    await expect(page).toHaveURL(/\/metrics$/)
  })
})
```

## Gate
`.claude/scripts/dev.sh format && .claude/scripts/dev.sh typecheck && .claude/scripts/dev.sh lint` all pass, and `grep -rn "is_superuser" src tests --exclude-dir=client` prints nothing.
