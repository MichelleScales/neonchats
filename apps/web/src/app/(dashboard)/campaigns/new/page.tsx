"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { campaigns } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const CHANNELS = ["email", "social", "landing_page", "ad"];

export default function NewCampaignPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    name: "",
    goal: "",
    audience_summary: "",
    channels: [] as string[],
    offer: { headline: "", cta: "" },
    brief: "",
    compliance_notes: "",
    launch_at: "",
  });

  const mutation = useMutation({
    mutationFn: (data: typeof form) => campaigns.create(data),
    onSuccess: (created) => {
      toast.success("Campaign created");
      router.push(`/campaigns/${created.id}`);
    },
    onError: () => toast.error("Failed to create campaign"),
  });

  const toggle = (ch: string) =>
    setForm((f) => ({
      ...f,
      channels: f.channels.includes(ch) ? f.channels.filter((c) => c !== ch) : [...f.channels, ch],
    }));

  const set = (key: string, val: string) => setForm((f) => ({ ...f, [key]: val }));

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">New Campaign</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Define the campaign brief, audience, and channels.
        </p>
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); mutation.mutate(form); }}
        className="space-y-6"
      >
        <Section title="Basics">
          <Field label="Campaign name" required>
            <input
              className="input"
              placeholder="Summer Sale 2026"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              required
            />
          </Field>
          <Field label="Goal">
            <textarea
              className="input min-h-[80px]"
              placeholder="Drive 500 trial sign-ups from email + social"
              value={form.goal}
              onChange={(e) => set("goal", e.target.value)}
            />
          </Field>
        </Section>

        <Section title="Audience">
          <Field label="Audience summary">
            <textarea
              className="input min-h-[80px]"
              placeholder="SMB founders in SaaS, 10-50 employees, US market"
              value={form.audience_summary}
              onChange={(e) => set("audience_summary", e.target.value)}
            />
          </Field>
        </Section>

        <Section title="Offer">
          <Field label="Headline">
            <input
              className="input"
              placeholder="Start free — no credit card needed"
              value={form.offer.headline}
              onChange={(e) => setForm((f) => ({ ...f, offer: { ...f.offer, headline: e.target.value } }))}
            />
          </Field>
          <Field label="CTA">
            <input
              className="input"
              placeholder="Get started free"
              value={form.offer.cta}
              onChange={(e) => setForm((f) => ({ ...f, offer: { ...f.offer, cta: e.target.value } }))}
            />
          </Field>
        </Section>

        <Section title="Channels">
          <div className="flex gap-2 flex-wrap">
            {CHANNELS.map((ch) => (
              <button
                key={ch}
                type="button"
                onClick={() => toggle(ch)}
                className={cn(
                  "text-sm px-3 py-1.5 rounded-md border transition-colors capitalize",
                  form.channels.includes(ch)
                    ? "bg-primary text-primary-foreground border-primary"
                    : "border-border text-muted-foreground hover:border-foreground"
                )}
              >
                {ch.replace("_", " ")}
              </button>
            ))}
          </div>
        </Section>

        <Section title="Brief">
          <Field label="Campaign brief">
            <textarea
              className="input min-h-[120px]"
              placeholder="Tone should be urgent but friendly. Emphasise the free trial. Avoid mentioning competitors."
              value={form.brief}
              onChange={(e) => set("brief", e.target.value)}
            />
          </Field>
          <Field label="Compliance notes">
            <textarea
              className="input"
              placeholder="No health claims. Follow FTC disclosure rules."
              value={form.compliance_notes}
              onChange={(e) => set("compliance_notes", e.target.value)}
            />
          </Field>
        </Section>

        <Section title="Timeline">
          <Field label="Launch date">
            <input
              type="date"
              className="input"
              value={form.launch_at}
              onChange={(e) => set("launch_at", e.target.value)}
            />
          </Field>
        </Section>

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={mutation.isPending}
            className="rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
          >
            {mutation.isPending ? "Creating…" : "Create Campaign"}
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="rounded-md border border-border px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-4">
      <h2 className="text-sm font-medium text-foreground border-b border-border pb-2">{title}</h2>
      {children}
    </div>
  );
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm text-muted-foreground">
        {label} {required && <span className="text-destructive">*</span>}
      </label>
      {children}
    </div>
  );
}
