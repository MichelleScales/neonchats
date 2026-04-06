"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { campaigns, content } from "@/lib/api";
import { cn, formatDateTime } from "@/lib/utils";
import { useState } from "react";
import { toast } from "sonner";
import { RefreshCw, Send, AlertTriangle } from "lucide-react";

export default function ContentPage() {
  const qc = useQueryClient();
  const { data: campaignData } = useQuery({
    queryKey: ["campaigns"],
    queryFn: () => campaigns.list({ page_size: 100 }),
  });

  const [selectedCampaign, setSelectedCampaign] = useState("");
  const [rewriteId, setRewriteId] = useState<string | null>(null);
  const [rewriteInstr, setRewriteInstr] = useState("");

  const rewrite = useMutation({
    mutationFn: ({ id, instruction }: { id: string; instruction: string }) =>
      content.rewrite(id, { instruction }),
    onSuccess: () => { toast.success("Rewrite complete"); setRewriteId(null); setRewriteInstr(""); },
    onError: () => toast.error("Rewrite failed"),
  });

  const submit = useMutation({
    mutationFn: (id: string) => content.submit(id),
    onSuccess: () => toast.success("Submitted for approval"),
    onError: () => toast.error("Submit failed"),
  });

  const { data: campaignDetail } = useQuery({
    queryKey: ["campaign", selectedCampaign],
    queryFn: () => campaigns.get(selectedCampaign),
    enabled: !!selectedCampaign,
  });

  // Collect all assets across variants
  const assets = campaignDetail ? [] : []; // Assets are fetched per campaign detail

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Content Factory</h1>
        <p className="text-sm text-muted-foreground mt-1">
          View, edit, and submit generated assets.
        </p>
      </div>

      {/* Campaign selector */}
      <div className="flex items-center gap-3">
        <label className="text-sm text-muted-foreground">Campaign</label>
        <select
          className="input text-sm max-w-xs"
          value={selectedCampaign}
          onChange={(e) => setSelectedCampaign(e.target.value)}
        >
          <option value="">Select a campaign…</option>
          {campaignData?.items?.map((c: any) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      {!selectedCampaign && (
        <div className="rounded-lg border border-dashed border-border py-16 text-center text-sm text-muted-foreground">
          Select a campaign to view its content assets.
        </div>
      )}

      {selectedCampaign && !campaignDetail && (
        <div className="text-sm text-muted-foreground">Loading…</div>
      )}

      {campaignDetail && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Showing assets for <strong>{campaignDetail.name}</strong>. Generate assets from the campaign detail page.
          </p>

          {/* Rewrite modal */}
          {rewriteId && (
            <div className="rounded-lg border border-border p-4 bg-accent/30 space-y-3">
              <p className="text-sm font-medium">Rewrite instruction</p>
              <textarea
                className="input w-full min-h-[80px] text-sm"
                placeholder="e.g. Make it shorter and more urgent. Remove the price mention."
                value={rewriteInstr}
                onChange={(e) => setRewriteInstr(e.target.value)}
              />
              <div className="flex gap-2">
                <button
                  onClick={() => rewrite.mutate({ id: rewriteId, instruction: rewriteInstr })}
                  disabled={rewrite.isPending || !rewriteInstr}
                  className="text-xs px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  {rewrite.isPending ? "Rewriting…" : "Rewrite"}
                </button>
                <button
                  onClick={() => setRewriteId(null)}
                  className="text-xs px-3 py-1.5 rounded-md border border-border text-muted-foreground hover:text-foreground"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          <div className="text-sm text-muted-foreground">
            Navigate to the{" "}
            <strong>Campaign detail</strong> page to generate and view assets.
          </div>
        </div>
      )}
    </div>
  );
}
