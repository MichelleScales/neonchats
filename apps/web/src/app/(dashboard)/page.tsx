"use client";

import { useQuery } from "@tanstack/react-query";
import { campaigns, approvals, analytics } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import Link from "next/link";
import { Megaphone, CheckSquare, Zap, Activity } from "lucide-react";

export default function HomePage() {
  const { data: campaignData } = useQuery({
    queryKey: ["campaigns"],
    queryFn: () => campaigns.list({ page_size: 5 }),
  });
  const { data: pendingApprovals } = useQuery({
    queryKey: ["approvals", "pending"],
    queryFn: () => approvals.list({ status: "pending" }),
  });
  const { data: summary } = useQuery({
    queryKey: ["analytics-summary"],
    queryFn: () => analytics.summary(),
  });

  const stats = [
    {
      label: "Active Campaigns",
      value: campaignData?.total ?? "—",
      icon: Megaphone,
      href: "/campaigns",
    },
    {
      label: "Pending Approvals",
      value: pendingApprovals?.length ?? "—",
      icon: CheckSquare,
      href: "/approvals",
      alert: (pendingApprovals?.length ?? 0) > 0,
    },
    {
      label: "Assets Generated",
      value: summary?.assets_generated ?? "—",
      icon: Zap,
      href: "/content",
    },
    {
      label: "Total Sends",
      value: summary?.total_sends ?? "—",
      icon: Activity,
      href: "/analytics",
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Workspace</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Overview of active campaigns, approvals, and execution health.
        </p>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {stats.map(({ label, value, icon: Icon, href, alert }) => (
          <Link
            key={label}
            href={href}
            className="rounded-lg border border-border bg-card p-4 hover:bg-accent transition-colors"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted-foreground">{label}</span>
              <Icon className={cn("h-4 w-4", alert ? "text-destructive" : "text-muted-foreground")} />
            </div>
            <div className={cn("text-2xl font-semibold", alert && "text-destructive")}>
              {value}
            </div>
          </Link>
        ))}
      </div>

      {/* Recent campaigns */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium">Recent Campaigns</h2>
          <Link href="/campaigns" className="text-xs text-muted-foreground hover:text-foreground">
            View all →
          </Link>
        </div>
        <div className="rounded-lg border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">Name</th>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">Status</th>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">Created</th>
              </tr>
            </thead>
            <tbody>
              {campaignData?.items?.length ? (
                campaignData.items.map((c: any) => (
                  <tr key={c.id} className="border-t border-border hover:bg-muted/20">
                    <td className="px-4 py-3">
                      <Link href={`/campaigns/${c.id}`} className="hover:underline font-medium">
                        {c.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={c.status} />
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{formatDate(c.created_at)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={3} className="px-4 py-8 text-center text-muted-foreground text-sm">
                    No campaigns yet.{" "}
                    <Link href="/campaigns/new" className="underline">
                      Create one
                    </Link>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pending approvals */}
      {(pendingApprovals?.length ?? 0) > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-destructive">
              Approvals Waiting ({pendingApprovals.length})
            </h2>
            <Link href="/approvals" className="text-xs text-muted-foreground hover:text-foreground">
              Go to queue →
            </Link>
          </div>
          <div className="rounded-lg border border-destructive/30 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-destructive/5">
                <tr>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">Type</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">Due</th>
                  <th className="px-4 py-2.5" />
                </tr>
              </thead>
              <tbody>
                {pendingApprovals.map((a: any) => (
                  <tr key={a.id} className="border-t border-border">
                    <td className="px-4 py-3 capitalize">{a.approval_type}</td>
                    <td className="px-4 py-3 text-muted-foreground">{formatDate(a.due_date)}</td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/approvals/${a.id}`}
                        className="text-xs text-primary hover:underline"
                      >
                        Review →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: "bg-muted text-muted-foreground",
    pending_approval: "bg-yellow-100 text-yellow-800",
    approved: "bg-green-100 text-green-800",
    executing: "bg-blue-100 text-blue-800",
    live: "bg-emerald-100 text-emerald-800",
    archived: "bg-gray-100 text-gray-500",
  };
  return (
    <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", colors[status] ?? "bg-muted text-muted-foreground")}>
      {status.replace("_", " ")}
    </span>
  );
}
