"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { approvals } from "@/lib/api";
import { cn, formatDate, formatDateTime } from "@/lib/utils";
import { toast } from "sonner";
import { CheckCircle, XCircle, MessageSquare } from "lucide-react";

export default function ApprovalsPage() {
  const [statusFilter, setStatusFilter] = useState("pending");
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["approvals", statusFilter],
    queryFn: () => approvals.list({ status: statusFilter || undefined }),
  });

  const decide = useMutation({
    mutationFn: ({ id, decision, comment }: { id: string; decision: string; comment?: string }) =>
      approvals.decide(id, { decision, comment }),
    onSuccess: () => {
      toast.success("Decision recorded");
      qc.invalidateQueries({ queryKey: ["approvals"] });
    },
    onError: () => toast.error("Failed to record decision"),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Approvals</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Review content, spend, and publish decisions.
        </p>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2">
        {["pending", "approved", "rejected", "changes_requested", ""].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={cn(
              "text-xs px-3 py-1.5 rounded-full border transition-colors",
              statusFilter === s
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border text-muted-foreground hover:border-foreground hover:text-foreground"
            )}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {isLoading && (
          <div className="text-sm text-muted-foreground py-10 text-center">Loading…</div>
        )}
        {!isLoading && !data?.length && (
          <div className="text-sm text-muted-foreground py-10 text-center rounded-lg border border-border">
            No approvals in this state.
          </div>
        )}
        {data?.map((a: any) => (
          <ApprovalCard key={a.id} approval={a} onDecide={decide.mutate} deciding={decide.isPending} />
        ))}
      </div>
    </div>
  );
}

function ApprovalCard({
  approval: a,
  onDecide,
  deciding,
}: {
  approval: any;
  onDecide: (args: { id: string; decision: string; comment?: string }) => void;
  deciding: boolean;
}) {
  const [comment, setComment] = useState("");
  const [open, setOpen] = useState(false);

  const policyFail = Object.values(a.policy_check_results).some((v) => v === "fail");

  return (
    <div className={cn(
      "rounded-lg border p-4 space-y-3",
      a.status === "pending" ? "border-border" : "border-border/50 opacity-70"
    )}>
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm capitalize">{a.approval_type} approval</span>
            <StatusPill status={a.status} />
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            Due {formatDate(a.due_date)} · Created {formatDateTime(a.created_at)}
          </div>
        </div>
        {a.status === "pending" && (
          <div className="flex gap-2">
            <button
              onClick={() => onDecide({ id: a.id, decision: "approved", comment })}
              disabled={deciding}
              className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
            >
              <CheckCircle className="h-3.5 w-3.5" />
              Approve
            </button>
            <button
              onClick={() => onDecide({ id: a.id, decision: "rejected", comment })}
              disabled={deciding}
              className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md bg-destructive text-white hover:bg-destructive/90 disabled:opacity-50"
            >
              <XCircle className="h-3.5 w-3.5" />
              Reject
            </button>
            <button
              onClick={() => setOpen((v) => !v)}
              className="inline-flex items-center gap-1.5 text-xs px-2 py-1.5 rounded-md border border-border text-muted-foreground hover:text-foreground"
            >
              <MessageSquare className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Policy checks */}
      {Object.keys(a.policy_check_results).length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {Object.entries(a.policy_check_results).map(([k, v]) => (
            <span
              key={k}
              className={cn(
                "text-xs px-2 py-0.5 rounded-full",
                v === "pass" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
              )}
            >
              {k}: {String(v)}
            </span>
          ))}
        </div>
      )}

      {/* Comment box */}
      {open && (
        <div className="space-y-2">
          <textarea
            className="input text-sm min-h-[70px] w-full"
            placeholder="Add a comment (optional)…"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
        </div>
      )}

      {/* Existing comments */}
      {a.comments?.length > 0 && (
        <div className="space-y-2 pt-1">
          {a.comments.map((c: any) => (
            <div key={c.id} className="text-xs bg-muted/40 rounded px-3 py-2">
              <span className="font-medium">{c.author_id.slice(0, 8)}…</span>{" "}
              <span className="text-muted-foreground">{formatDateTime(c.created_at)}</span>
              <p className="mt-0.5">{c.body}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    approved: "bg-green-100 text-green-700",
    rejected: "bg-red-100 text-red-700",
    changes_requested: "bg-orange-100 text-orange-700",
  };
  return (
    <span className={cn("text-xs px-2 py-0.5 rounded-full capitalize", colors[status] ?? "bg-muted text-muted-foreground")}>
      {status.replace(/_/g, " ")}
    </span>
  );
}
