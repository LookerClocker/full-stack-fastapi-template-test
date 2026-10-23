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
