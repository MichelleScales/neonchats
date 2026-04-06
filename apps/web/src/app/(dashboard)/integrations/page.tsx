"use client";

import { useQuery } from "@tanstack/react-query";
import { integrations } from "@/lib/api";
import { CheckCircle, XCircle, Loader2, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";

interface IntegrationStatus {
  sendgrid: { connected: boolean; from_email: string | null };
  hubspot: { connected: boolean; portal_id?: number; hub_domain?: string; error?: string };
  google_ads: { connected: boolean };
  meta_ads: { connected: boolean };
  klaviyo: { connected: boolean };
  webflow: { connected: boolean };
}

interface HubSpotList {
  id: string;
  name: string;
  size: number;
  list_type: string;
}

const INTEGRATION_META: Record<string, { label: string; category: string; description: string; docsUrl: string }> = {
  sendgrid: {
    label: "SendGrid",
    category: "Email",
    description: "Transactional and marketing email delivery via SendGrid v3 API.",
    docsUrl: "https://docs.sendgrid.com/api-reference",
  },
  hubspot: {
    label: "HubSpot",
    category: "CRM",
    description: "Contact sync, list targeting for email sends, and deal management.",
    docsUrl: "https://developers.hubspot.com/docs/api/overview",
  },
  google_ads: {
    label: "Google Ads",
    category: "Ads",
    description: "Launch and manage paid search campaigns. (Phase 3)",
    docsUrl: "#",
  },
  meta_ads: {
    label: "Meta Ads",
    category: "Ads",
    description: "Facebook and Instagram ad management. (Phase 3)",
    docsUrl: "#",
  },
  klaviyo: {
    label: "Klaviyo",
    category: "Email",
    description: "E-commerce email and SMS automation. (Phase 3)",
    docsUrl: "#",
  },
  webflow: {
    label: "Webflow",
    category: "CMS",
    description: "Publish landing pages and web content. (Phase 3)",
    docsUrl: "#",
  },
};

export default function IntegrationsPage() {
  const [showHubSpotLists, setShowHubSpotLists] = useState(false);

  const { data: status, isLoading } = useQuery<IntegrationStatus>({
    queryKey: ["integrations", "status"],
    queryFn: () => integrations.status(),
    refetchInterval: 30_000,
  });

  const { data: hubspotLists, isLoading: listsLoading, error: listsError } = useQuery<HubSpotList[]>({
    queryKey: ["integrations", "hubspot", "lists"],
    queryFn: () => integrations.hubspotLists(),
    enabled: showHubSpotLists && !!status?.hubspot?.connected,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Integrations</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Connect your CRM, email, ads, and CMS providers.
          </p>
        </div>
        {isLoading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground mt-2" />}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(INTEGRATION_META).map(([key, meta]) => {
          const s = status ? (status as any)[key] : null;
          const connected = s?.connected ?? false;

          return (
            <div
              key={key}
              className={cn(
                "rounded-lg border p-4 space-y-3 transition-colors",
                connected ? "border-emerald-200 bg-emerald-50/30" : "border-border bg-card"
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="font-medium text-sm">{meta.label}</span>
                    <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                      {meta.category}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">{meta.description}</p>
                  {/* Extra detail for connected services */}
                  {key === "sendgrid" && s?.from_email && (
                    <p className="text-xs text-emerald-700 mt-1">From: {s.from_email}</p>
                  )}
                  {key === "hubspot" && s?.hub_domain && (
                    <p className="text-xs text-emerald-700 mt-1">Portal: {s.hub_domain} (#{s.portal_id})</p>
                  )}
                  {s?.error && (
                    <p className="text-xs text-red-500 mt-1">{s.error}</p>
                  )}
                </div>
                <div className="shrink-0">
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  ) : connected ? (
                    <CheckCircle className="h-4 w-4 text-emerald-600" />
                  ) : (
                    <XCircle className="h-4 w-4 text-muted-foreground" />
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                {connected ? (
                  <>
                    <span className="text-xs text-emerald-700 font-medium">Connected</span>
                    {key === "hubspot" && (
                      <button
                        onClick={() => setShowHubSpotLists(!showHubSpotLists)}
                        className="text-xs px-2.5 py-1 rounded-md border border-emerald-200 text-emerald-700 hover:bg-emerald-100 transition-colors"
                      >
                        {showHubSpotLists ? "Hide Lists" : "View Lists"}
                      </button>
                    )}
                  </>
                ) : (
                  <span className="text-xs text-muted-foreground">
                    {["google_ads", "meta_ads", "klaviyo", "webflow"].includes(key)
                      ? "Coming in Phase 3"
                      : "Add to .env to connect"}
                  </span>
                )}
                {meta.docsUrl !== "#" && (
                  <a
                    href={meta.docsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-auto text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
                  >
                    Docs <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* HubSpot Lists panel */}
      {showHubSpotLists && (
        <div className="rounded-lg border border-border bg-card overflow-hidden">
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <h2 className="text-sm font-medium">HubSpot Contact Lists</h2>
            {listsLoading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
          </div>
          {listsError ? (
            <div className="p-4 text-sm text-red-500">
              Failed to load lists. Check your HubSpot token.
            </div>
          ) : hubspotLists?.length === 0 ? (
            <div className="p-4 text-sm text-muted-foreground">No lists found in HubSpot.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/40">
                  <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">List Name</th>
                  <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">Type</th>
                  <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">Contacts</th>
                  <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">List ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {hubspotLists?.map((list) => (
                  <tr key={list.id} className="hover:bg-muted/20">
                    <td className="px-4 py-2.5 font-medium text-sm">{list.name}</td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground capitalize">{list.list_type.toLowerCase()}</td>
                    <td className="px-4 py-2.5 text-sm">{list.size.toLocaleString()}</td>
                    <td className="px-4 py-2.5 text-xs font-mono text-muted-foreground">{list.id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="px-4 py-2.5 border-t border-border bg-muted/20">
            <p className="text-xs text-muted-foreground">
              Use a List ID in campaign channel config (<code className="font-mono">hubspot_list_id</code>) to target that audience for email sends.
            </p>
          </div>
        </div>
      )}

      <div className="rounded-lg border border-dashed border-border p-5 text-center">
        <p className="text-sm text-muted-foreground">
          Phase 3 will add Google Ads, Meta Ads, Klaviyo, and Webflow via the MCP Gateway connector.
        </p>
      </div>
    </div>
  );
}
