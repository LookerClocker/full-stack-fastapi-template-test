import type { Role } from "@/client"

export const ROLE_LABELS: Record<Role, string> = {
  admin: "Admin",
  manager: "Manager",
  member: "Member",
}

export const ROLES = Object.keys(ROLE_LABELS) as Role[]
