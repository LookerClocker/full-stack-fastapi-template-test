import type { Permission } from "@/client"
import useAuth from "./useAuth"

export function usePermissions() {
  const { user } = useAuth()

  const can = (permission: Permission) =>
    user?.permissions.includes(permission) ?? false

  return { can, isLoaded: user != null }
}
