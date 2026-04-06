"use client";

import { useQuery } from "@tanstack/react-query";
import { campaigns } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import Link from "next/link";
import { Plus } from "lucide-react";
import { useState } from "react";

const STATUSES = ["", "draft", "pending_approval", "approved", "live", "archived"];

export default function CampaignsPage() {
  const [status, setStatus] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["campaigns", status],
    queryFn: () => campaigns.list({ status: status || undefined }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Campaigns</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {data?.total ?? 0} total
          </p>
        </div>
        <Link
          href="/campaigns/new"
          className="inline-flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm font-medium hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          New Campaign
        </Link>
      </div>

      {/* Status filter */}
      <div className="flex gap-2 flex-wrap">
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            className={cn(
              "text-xs px-3 py-1.5 rounded-full border transition-colors",
              status === s
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border text-muted-foreground hover:border-foreground hover:text-foreground"
            )}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">Name</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">Status</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">Channels</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">Launch</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">Created</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-muted-foreground">
                  Loading…
                </td>
              </tr>
            ) : data?.items?.length ? (
              data.items.map((c: any) => (
                <tr key={c.id} className="border-t border-border hover:bg-muted/20">
                  <td className="px-4 py-3">
                    <Link href={`/campaigns/${c.id}`} className="font-medium hover:underline">
                      {c.name}
                    </Link>
                    {c.goal && (
                      <p className="text-xs text-muted-foreground truncate max-w-xs">{c.goal}</p>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 flex-wrap">
                      {c.channels?.map((ch: any) => (
                        <span
                          key={ch.id}
                          className="text-xs bg-accent px-1.5 py-0.5 rounded capitalize"
                        >
                          {ch.channel}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">
                    {formatDate(c.launch_at)}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">
                    {formatDate(c.created_at)}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-muted-foreground">
                  No campaigns.{" "}
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
      {status.replace(/_/g, " ")}
    </span>
  );
}
