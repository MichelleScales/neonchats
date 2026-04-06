"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { voicePacks } from "@/lib/api";
import { toast } from "sonner";
import { cn, formatDate } from "@/lib/utils";
import { Plus, Upload, Globe } from "lucide-react";

export default function VoicePage() {
  const qc = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", style_summary: "", banned_phrases: "" });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [ingestUrl, setIngestUrl] = useState("");
  const [ingestContent, setIngestContent] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["voice-packs"],
    queryFn: () => voicePacks.list(),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      voicePacks.create({
        name: form.name,
        style_summary: form.style_summary,
        banned_phrases: form.banned_phrases
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
      }),
    onSuccess: () => {
      toast.success("Voice pack created");
      setCreating(false);
      setForm({ name: "", style_summary: "", banned_phrases: "" });
      qc.invalidateQueries({ queryKey: ["voice-packs"] });
    },
    onError: () => toast.error("Failed to create"),
  });

  const activateMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      voicePacks.update(id, { is_active }),
    onSuccess: () => {
      toast.success("Updated");
      qc.invalidateQueries({ queryKey: ["voice-packs"] });
    },
  });

  const ingestMutation = useMutation({
    mutationFn: () =>
      voicePacks.ingest(selectedId!, {
        source_type: ingestUrl ? "website" : "manual",
        source_url: ingestUrl || undefined,
        content: ingestContent || undefined,
      }),
    onSuccess: () => {
      toast.success("Document ingested");
      setIngestUrl("");
      setIngestContent("");
    },
    onError: () => toast.error("Ingest failed"),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Brand Voice</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage voice packs, banned phrases, and canon examples.
          </p>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="inline-flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm font-medium hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          New Voice Pack
        </button>
      </div>

      {/* Create form */}
      {creating && (
        <div className="rounded-lg border border-border p-4 space-y-4">
          <h2 className="text-sm font-medium">New Voice Pack</h2>
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground">Name</label>
            <input
              className="input text-sm"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="Default Brand Voice"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground">Style summary (used as AI prompt prefix)</label>
            <textarea
              className="input text-sm min-h-[100px]"
              value={form.style_summary}
              onChange={(e) => setForm((f) => ({ ...f, style_summary: e.target.value }))}
              placeholder="Friendly but professional. Direct and concise. Never use jargon. Always lead with value."
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground">Banned phrases (one per line)</label>
            <textarea
              className="input text-sm min-h-[80px]"
              value={form.banned_phrases}
              onChange={(e) => setForm((f) => ({ ...f, banned_phrases: e.target.value }))}
              placeholder={"synergy\nbest-in-class\ngame-changing"}
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending || !form.name}
              className="text-xs px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {createMutation.isPending ? "Creating…" : "Create"}
            </button>
            <button
              onClick={() => setCreating(false)}
              className="text-xs px-3 py-1.5 rounded-md border border-border text-muted-foreground"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Voice pack list */}
      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading…</div>
      ) : (
        <div className="space-y-3">
          {data?.map((vp: any) => (
            <div
              key={vp.id}
              className={cn(
                "rounded-lg border p-4 space-y-3",
                selectedId === vp.id ? "border-primary" : "border-border"
              )}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{vp.name}</span>
                    <span className="text-xs text-muted-foreground">v{vp.version}</span>
                    {vp.is_active && (
                      <span className="text-xs bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full">
                        Active
                      </span>
                    )}
                  </div>
                  {vp.style_summary && (
                    <p className="text-xs text-muted-foreground mt-1 max-w-lg truncate">{vp.style_summary}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => activateMutation.mutate({ id: vp.id, is_active: !vp.is_active })}
                    className="text-xs px-2.5 py-1 rounded-md border border-border text-muted-foreground hover:text-foreground"
                  >
                    {vp.is_active ? "Deactivate" : "Activate"}
                  </button>
                  <button
                    onClick={() => setSelectedId(selectedId === vp.id ? null : vp.id)}
                    className="text-xs px-2.5 py-1 rounded-md border border-border text-muted-foreground hover:text-foreground"
                  >
                    {selectedId === vp.id ? "Close" : "Ingest →"}
                  </button>
                </div>
              </div>

              {vp.banned_phrases?.length > 0 && (
                <div className="flex gap-1.5 flex-wrap">
                  {vp.banned_phrases.map((p: string) => (
                    <span key={p} className="text-xs bg-red-50 text-red-600 px-2 py-0.5 rounded">
                      {p}
                    </span>
                  ))}
                </div>
              )}

              {/* Ingest panel */}
              {selectedId === vp.id && (
                <div className="space-y-3 pt-2 border-t border-border">
                  <p className="text-xs font-medium">Ingest sample content</p>
                  <div className="space-y-1.5">
                    <label className="text-xs text-muted-foreground">Website URL (optional)</label>
                    <input
                      className="input text-sm"
                      placeholder="https://example.com/about"
                      value={ingestUrl}
                      onChange={(e) => setIngestUrl(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs text-muted-foreground">Or paste content directly</label>
                    <textarea
                      className="input text-sm min-h-[80px]"
                      placeholder="Paste brand copy, email examples, etc."
                      value={ingestContent}
                      onChange={(e) => setIngestContent(e.target.value)}
                    />
                  </div>
                  <button
                    onClick={() => ingestMutation.mutate()}
                    disabled={ingestMutation.isPending || (!ingestUrl && !ingestContent)}
                    className="inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                  >
                    {ingestUrl ? <Globe className="h-3.5 w-3.5" /> : <Upload className="h-3.5 w-3.5" />}
                    {ingestMutation.isPending ? "Ingesting…" : "Ingest"}
                  </button>
                </div>
              )}
            </div>
          ))}
          {!data?.length && !creating && (
            <div className="rounded-lg border border-dashed border-border py-12 text-center text-sm text-muted-foreground">
              No voice packs yet.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
