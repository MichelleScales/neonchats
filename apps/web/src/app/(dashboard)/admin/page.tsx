"use client";

import { useQuery } from "@tanstack/react-query";
import { auditLogs } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import { useState } from "react";

const ACTIONS = ["", "campaign.created", "content.generated", "approval.approved", "approval.rejected", "execution.success"];

export default function AdminPage() {
  const [action, setAction] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs", action],
    queryFn: () => auditLogs.list({ action: action || undefined }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Admin</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Audit log, users, and workspace settings.
        </p>
      </div>

      <div>
        <h2 className="text-sm font-medium mb-3">Audit Log</h2>
        <div className="flex gap-2 mb-4 flex-wrap">
          {ACTIONS.map((a) => (
            <button
              key={a}
              onClick={() => setAction(a)}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                action === a
                  ? "bg-primary text-primary-foreground border-primary"
                  : "border-border text-muted-foreground hover:border-foreground hover:text-foreground"
              }`}
            >
              {a || "All"}
            </button>
          ))}
        </div>

        <div className="rounded-lg border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">Time</th>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">Action</th>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">Actor</th>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">Summary</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">Loading…</td>
                </tr>
              ) : data?.length ? (
                data.map((log: any) => (
                  <tr key={log.id} className="border-t border-border hover:bg-muted/20">
                    <td className="px-4 py-2.5 text-xs text-muted-foreground whitespace-nowrap">
                      {formatDateTime(log.occurred_at)}
                    </td>
                    <td className="px-4 py-2.5">
                      <code className="text-xs bg-muted px-1.5 py-0.5 rounded">{log.action}</code>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">
                      {log.actor_email || log.actor_id?.slice(0, 8) || "system"}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground truncate max-w-xs">
                      {log.summary || "—"}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                    No audit events yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
