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
