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
