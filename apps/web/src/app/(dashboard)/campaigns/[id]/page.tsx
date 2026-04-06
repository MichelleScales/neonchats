"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { campaigns, content, executions, approvals } from "@/lib/api";
import { cn, formatDate, formatDateTime } from "@/lib/utils";
import { useState } from "react";
import { toast } from "sonner";
import { Zap, RefreshCw, Send, ChevronDown, ChevronRight, CheckCircle, XCircle, Clock, AlertCircle } from "lucide-react";
import Link from "next/link";

// ─── Types ─────────────────────────────────────────────────────────────────

interface ContentVariant {
  id: string;
  variant_index: number;
  is_active: boolean;
  body: Record<string, unknown>;
  created_at: string;
}

interface ContentAsset {
  id: string;
  asset_type: string;
  status: string;
  created_at: string;
  updated_at: string;
  variants: ContentVariant[];
}

interface ExecutionRun {
  id: string;
  channel: string;
  provider: string;
  status: string;
  error_message: string | null;
  provider_id: string | null;
  created_at: string;
  asset_id: string;
}

// ─── Main Page ─────────────────────────────────────────────────────────────

export default function CampaignDetailPage({ params }: { params: { id: string } }) {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<"content" | "executions">("content");
  const [genType, setGenType] = useState("email");
  const [genCount, setGenCount] = useState(2);
  const [execProvider, setExecProvider] = useState("sendgrid");
  const [execApprovalId, setExecApprovalId] = useState("");

  const { data: campaign, isLoading } = useQuery({
    queryKey: ["campaign", params.id],
    queryFn: () => campaigns.get(params.id),
  });

  const { data: assets = [] } = useQuery<ContentAsset[]>({
    queryKey: ["content", "campaign", params.id],
    queryFn: () => content.listByCampaign(params.id),
    enabled: !!params.id,
  });

  const { data: runs = [] } = useQuery<ExecutionRun[]>({
    queryKey: ["executions", "campaign", params.id],
    queryFn: () => executions.listByCampaign(params.id),
    enabled: !!params.id && activeTab === "executions",
    refetchInterval: activeTab === "executions" ? 8000 : false,
  });

  const generateMutation = useMutation({
    mutationFn: () =>
      content.generate({
        campaign_id: params.id,
        asset_type: genType,
        variant_count: genCount,
      }),
    onSuccess: () => {
      toast.success("Content generated");
      qc.invalidateQueries({ queryKey: ["content", "campaign", params.id] });
    },
    onError: (e: any) =>
      toast.error(e.response?.data?.detail || "Generation failed"),
  });

  const updateStatus = useMutation({
    mutationFn: (status: string) => campaigns.update(params.id, { status }),
    onSuccess: () => {
      toast.success("Status updated");
      qc.invalidateQueries({ queryKey: ["campaign", params.id] });
    },
  });

  const submitAsset = useMutation({
    mutationFn: (assetId: string) => content.submit(assetId),
    onSuccess: () => {
      toast.success("Asset submitted for approval");
      qc.invalidateQueries({ queryKey: ["content", "campaign", params.id] });
    },
    onError: (e: any) =>
      toast.error(e.response?.data?.detail || "Submit failed"),
  });

  const runExec = useMutation({
    mutationFn: ({ assetId, channel }: { assetId: string; channel: string }) =>
      executions.run({
        campaign_id: params.id,
        asset_id: assetId,
        channel,
        provider: execProvider,
        approval_id: execApprovalId,
      }),
    onSuccess: () => {
      toast.success("Execution dispatched");
      qc.invalidateQueries({ queryKey: ["executions", "campaign", params.id] });
      setActiveTab("executions");
    },
    onError: (e: any) =>
      toast.error(e.response?.data?.detail || "Execution failed"),
  });

  const retryRun = useMutation({
    mutationFn: (runId: string) => executions.retry(runId),
    onSuccess: () => {
      toast.success("Retry queued");
      qc.invalidateQueries({ queryKey: ["executions", "campaign", params.id] });
    },
    onError: (e: any) =>
      toast.error(e.response?.data?.detail || "Retry failed"),
  });

  if (isLoading) return <div className="text-muted-foreground text-sm p-8">Loading…</div>;
  if (!campaign) return <div className="text-muted-foreground text-sm p-8">Campaign not found.</div>;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link href="/campaigns" className="text-xs text-muted-foreground hover:text-foreground mb-2 inline-block">
            ← Campaigns
          </Link>
          <h1 className="text-2xl font-semibold">{campaign.name}</h1>
          {campaign.goal && (
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl">{campaign.goal}</p>
          )}
        </div>
        <div className="flex items-center gap-2 mt-6">
          <StatusBadge status={campaign.status} />
          {campaign.status === "draft" && (
            <button
              onClick={() => updateStatus.mutate("pending_approval")}
              disabled={updateStatus.isPending}
              className="text-xs px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              Submit Campaign
            </button>
          )}
        </div>
      </div>

      {/* Meta row */}
      <div className="flex flex-wrap gap-4 text-sm">
        {campaign.audience_summary && (
          <MetaPill label="Audience" value={campaign.audience_summary} />
        )}
        {campaign.launch_at && (
          <MetaPill label="Launch" value={formatDate(campaign.launch_at)} />
        )}
        {campaign.budget && (
          <MetaPill label="Budget" value={`$${Number(campaign.budget).toLocaleString()}`} />
        )}
        {campaign.channels?.map((ch: any) => (
          <MetaPill key={ch.id} label="Channel" value={ch.channel} />
        ))}
      </div>

      {/* Compliance */}
      {campaign.compliance_notes && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 flex gap-2 items-start">
          <AlertCircle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
          <p className="text-xs text-amber-700">{campaign.compliance_notes}</p>
        </div>
      )}

      {/* Generate bar */}
      <div className="rounded-lg border border-border p-4 bg-card">
        <h2 className="text-sm font-medium mb-3">Generate Content</h2>
        <div className="flex flex-wrap gap-3 items-end">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Asset type</label>
            <select className="input text-sm" value={genType} onChange={(e) => setGenType(e.target.value)}>
              <option value="email">Email</option>
              <option value="social_post">Social Post</option>
              <option value="landing_page">Landing Page</option>
              <option value="ad_copy">Ad Copy</option>
            </select>
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Variants</label>
            <select className="input text-sm w-20" value={genCount} onChange={(e) => setGenCount(Number(e.target.value))}>
              {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="inline-flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
          >
            <Zap className="h-3.5 w-3.5" />
            {generateMutation.isPending ? "Generating…" : "Generate"}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div>
        <div className="flex gap-1 border-b border-border mb-4">
          {(["content", "executions"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                "px-4 py-2 text-sm font-medium capitalize -mb-px border-b-2 transition-colors",
                activeTab === tab
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {tab}
              {tab === "content" && assets.length > 0 && (
                <span className="ml-1.5 text-xs bg-muted rounded-full px-1.5 py-0.5">{assets.length}</span>
              )}
              {tab === "executions" && runs.length > 0 && (
                <span className="ml-1.5 text-xs bg-muted rounded-full px-1.5 py-0.5">{runs.length}</span>
              )}
            </button>
          ))}
        </div>

        {activeTab === "content" && (
          <ContentTab
            assets={assets}
            onSubmit={(id) => submitAsset.mutate(id)}
            onExecute={(assetId, channel) => runExec.mutate({ assetId, channel })}
            execProvider={execProvider}
            setExecProvider={setExecProvider}
            execApprovalId={execApprovalId}
            setExecApprovalId={setExecApprovalId}
            isSubmitting={submitAsset.isPending}
            isExecuting={runExec.isPending}
          />
        )}

        {activeTab === "executions" && (
          <ExecutionsTab runs={runs} onRetry={(id) => retryRun.mutate(id)} isRetrying={retryRun.isPending} />
        )}
      </div>
    </div>
  );
}

// ─── Content Tab ───────────────────────────────────────────────────────────

function ContentTab({
  assets,
  onSubmit,
  onExecute,
  execProvider,
  setExecProvider,
  execApprovalId,
  setExecApprovalId,
  isSubmitting,
  isExecuting,
}: {
  assets: ContentAsset[];
  onSubmit: (id: string) => void;
  onExecute: (assetId: string, channel: string) => void;
  execProvider: string;
  setExecProvider: (v: string) => void;
  execApprovalId: string;
  setExecApprovalId: (v: string) => void;
  isSubmitting: boolean;
  isExecuting: boolean;
}) {
  if (assets.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground text-sm">
        No content assets yet. Use the generator above to create some.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {assets.map((asset) => (
        <AssetCard
          key={asset.id}
          asset={asset}
          onSubmit={onSubmit}
          onExecute={onExecute}
          execProvider={execProvider}
          setExecProvider={setExecProvider}
          execApprovalId={execApprovalId}
          setExecApprovalId={setExecApprovalId}
          isSubmitting={isSubmitting}
          isExecuting={isExecuting}
        />
      ))}
    </div>
  );
}

function AssetCard({
  asset,
  onSubmit,
  onExecute,
  execProvider,
  setExecProvider,
  execApprovalId,
  setExecApprovalId,
  isSubmitting,
  isExecuting,
}: {
  asset: ContentAsset;
  onSubmit: (id: string) => void;
  onExecute: (assetId: string, channel: string) => void;
  execProvider: string;
  setExecProvider: (v: string) => void;
  execApprovalId: string;
  setExecApprovalId: (v: string) => void;
  isSubmitting: boolean;
  isExecuting: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [showExecute, setShowExecute] = useState(false);
  const [execChannel, setExecChannel] = useState("email");
  const activeVariant = asset.variants?.find((v) => v.is_active) ?? asset.variants?.[0];

  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      {/* Asset header row */}
      <div className="flex items-center gap-3 p-4">
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-muted-foreground hover:text-foreground"
        >
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium capitalize">{asset.asset_type.replace(/_/g, " ")}</span>
            <AssetStatusBadge status={asset.status} />
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            {asset.variants?.length ?? 0} variant{asset.variants?.length !== 1 ? "s" : ""} · Created {formatDateTime(asset.created_at)}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {asset.status === "draft" && (
            <button
              onClick={() => onSubmit(asset.id)}
              disabled={isSubmitting}
              className="text-xs px-3 py-1.5 rounded-md border border-border hover:bg-accent disabled:opacity-50 flex items-center gap-1"
            >
              <Send className="h-3 w-3" />
              Submit
            </button>
          )}
          {asset.status === "approved" && (
            <button
              onClick={() => setShowExecute(!showExecute)}
              className="text-xs px-3 py-1.5 rounded-md bg-emerald-600 text-white hover:bg-emerald-700 flex items-center gap-1"
            >
              <Zap className="h-3 w-3" />
              Execute
            </button>
          )}
        </div>
      </div>

      {/* Execute panel */}
      {showExecute && asset.status === "approved" && (
        <div className="border-t border-border bg-muted/30 p-4 space-y-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Execute via provider</p>
          <div className="flex flex-wrap gap-3 items-end">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Channel</label>
              <select className="input text-sm" value={execChannel} onChange={(e) => setExecChannel(e.target.value)}>
                <option value="email">Email</option>
                <option value="social">Social</option>
                <option value="sms">SMS</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Provider</label>
              <select className="input text-sm" value={execProvider} onChange={(e) => setExecProvider(e.target.value)}>
                <option value="sendgrid">SendGrid</option>
                <option value="hubspot">HubSpot</option>
                <option value="klaviyo">Klaviyo</option>
              </select>
            </div>
            <div className="space-y-1 flex-1 min-w-48">
              <label className="text-xs text-muted-foreground">Approval ID</label>
              <input
                className="input text-sm w-full font-mono"
                placeholder="UUID of approved approval"
                value={execApprovalId}
                onChange={(e) => setExecApprovalId(e.target.value)}
              />
            </div>
            <button
              onClick={() => onExecute(asset.id, execChannel)}
              disabled={isExecuting || !execApprovalId}
              className="inline-flex items-center gap-2 rounded-md bg-emerald-600 text-white px-4 py-2 text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
            >
              <Send className="h-3.5 w-3.5" />
              {isExecuting ? "Sending…" : "Send"}
            </button>
          </div>
        </div>
      )}

      {/* Expanded variants */}
      {expanded && (
        <div className="border-t border-border">
          {asset.variants?.length ? (
            asset.variants.map((variant) => (
              <VariantRow key={variant.id} variant={variant} />
            ))
          ) : (
            <div className="p-4 text-xs text-muted-foreground">No variants found.</div>
          )}
        </div>
      )}
    </div>
  );
}

function VariantRow({ variant }: { variant: ContentVariant }) {
  const [open, setOpen] = useState(variant.is_active);
  const body = variant.body ?? {};

  return (
    <div className={cn("border-b border-border last:border-0", variant.is_active && "bg-emerald-50/50")}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-accent/50 transition-colors"
      >
        {open ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
        <span className="text-xs font-medium">Variant {variant.variant_index + 1}</span>
        {variant.is_active && (
          <span className="text-[10px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full font-medium">Active</span>
        )}
        <span className="ml-auto text-xs text-muted-foreground">{formatDateTime(variant.created_at)}</span>
      </button>
      {open && (
        <div className="px-8 pb-4 space-y-3">
          {Object.entries(body).map(([key, val]) => (
            <div key={key}>
              <div className="text-xs text-muted-foreground capitalize mb-1">{key.replace(/_/g, " ")}</div>
              {typeof val === "string" ? (
                <p className="text-sm leading-relaxed whitespace-pre-wrap bg-muted/50 rounded p-2 text-xs">{val}</p>
              ) : Array.isArray(val) ? (
                <div className="flex flex-wrap gap-1">
                  {(val as string[]).map((item, i) => (
                    <span key={i} className="text-xs bg-accent px-2 py-0.5 rounded">#{item}</span>
                  ))}
                </div>
              ) : (
                <pre className="text-xs bg-muted/50 rounded p-2 overflow-auto">{JSON.stringify(val, null, 2)}</pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Executions Tab ─────────────────────────────────────────────────────────

function ExecutionsTab({
  runs,
  onRetry,
  isRetrying,
}: {
  runs: ExecutionRun[];
  onRetry: (id: string) => void;
  isRetrying: boolean;
}) {
  if (runs.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground text-sm">
        No executions yet. Approve an asset and use Execute to send it.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/40">
            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">Status</th>
            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">Channel</th>
            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">Provider</th>
            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">Provider ID</th>
            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground">When</th>
            <th className="px-4 py-2.5" />
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {runs.map((run) => (
            <tr key={run.id} className="hover:bg-muted/20 transition-colors">
              <td className="px-4 py-3">
                <RunStatusBadge status={run.status} />
              </td>
              <td className="px-4 py-3 capitalize text-sm">{run.channel}</td>
              <td className="px-4 py-3 text-sm text-muted-foreground">{run.provider}</td>
              <td className="px-4 py-3 text-xs text-muted-foreground font-mono truncate max-w-[140px]">
                {run.provider_id ?? "—"}
              </td>
              <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                {formatDateTime(run.created_at)}
              </td>
              <td className="px-4 py-3 text-right">
                {run.status === "failed" && (
                  <div className="space-y-1">
                    <button
                      onClick={() => onRetry(run.id)}
                      disabled={isRetrying}
                      className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded border border-border hover:bg-accent disabled:opacity-50"
                    >
                      <RefreshCw className="h-3 w-3" />
                      Retry
                    </button>
                    {run.error_message && (
                      <p className="text-[10px] text-red-500 max-w-[180px] truncate" title={run.error_message}>
                        {run.error_message}
                      </p>
                    )}
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Shared UI helpers ──────────────────────────────────────────────────────

function MetaPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5 text-xs bg-muted rounded-md px-2.5 py-1.5">
      <span className="text-muted-foreground">{label}:</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: "bg-muted text-muted-foreground",
    pending_approval: "bg-yellow-100 text-yellow-800",
    approved: "bg-green-100 text-green-800",
    live: "bg-emerald-100 text-emerald-800",
    archived: "bg-gray-100 text-gray-500",
  };
  return (
    <span className={cn("text-xs px-2.5 py-1 rounded-full font-medium capitalize", colors[status] ?? "bg-muted text-muted-foreground")}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

function AssetStatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; icon: React.ReactNode }> = {
    draft: { color: "text-muted-foreground", icon: <Clock className="h-3 w-3" /> },
    pending_approval: { color: "text-yellow-600", icon: <Clock className="h-3 w-3" /> },
    approved: { color: "text-emerald-600", icon: <CheckCircle className="h-3 w-3" /> },
    rejected: { color: "text-red-500", icon: <XCircle className="h-3 w-3" /> },
  };
  const cfg = map[status] ?? map.draft;
  return (
    <span className={cn("inline-flex items-center gap-1 text-xs capitalize", cfg.color)}>
      {cfg.icon}
      {status.replace(/_/g, " ")}
    </span>
  );
}

function RunStatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    queued: "bg-blue-100 text-blue-700",
    running: "bg-yellow-100 text-yellow-700",
    success: "bg-emerald-100 text-emerald-700",
    failed: "bg-red-100 text-red-700",
  };
  return (
    <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium capitalize", map[status] ?? "bg-muted text-muted-foreground")}>
      {status}
    </span>
  );
}
