"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { integrations, connectors } from "@/lib/api";
import { CheckCircle, XCircle, Loader2, ExternalLink, Plus, Trash2, ShieldCheck, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";
import { toast } from "sonner";

// ── Provider metadata ────────────────────────────────────────────────────────

const PROVIDER_META: Record<string, {
  label: string;
  category: string;
  description: string;
  docsUrl: string;
  credentialFields: { key: string; label: string; secret?: boolean; placeholder?: string }[];
}> = {
  sendgrid: {
    label: "SendGrid",
    category: "Email",
    description: "Transactional and marketing email delivery.",
    docsUrl: "https://docs.sendgrid.com/api-reference",
    credentialFields: [
      { key: "api_key", label: "API Key", secret: true, placeholder: "SG...." },
      { key: "from_email", label: "From Email", placeholder: "noreply@yourdomain.com" },
    ],
  },
  klaviyo: {
    label: "Klaviyo",
    category: "Email / SMS",
    description: "Email and SMS campaigns via Klaviyo lists.",
    docsUrl: "https://developers.klaviyo.com",
    credentialFields: [
      { key: "api_key", label: "Private API Key", secret: true, placeholder: "pk_..." },
      { key: "list_id", label: "Default List ID", placeholder: "ABC123" },
      { key: "from_email", label: "From Email", placeholder: "noreply@yourdomain.com" },
    ],
  },
  meta_ads: {
    label: "Meta Ads",
    category: "Ads",
    description: "Facebook and Instagram ad creative via Marketing API.",
    docsUrl: "https://developers.facebook.com/docs/marketing-apis",
    credentialFields: [
      { key: "access_token", label: "Access Token", secret: true, placeholder: "EAAb..." },
      { key: "ad_account_id", label: "Ad Account ID", placeholder: "123456789" },
      { key: "page_id", label: "Page ID", placeholder: "987654321" },
    ],
  },
  google_ads: {
    label: "Google Ads",
    category: "Ads",
    description: "Responsive search ads via Google Ads API.",
    docsUrl: "https://developers.google.com/google-ads/api/docs/start",
    credentialFields: [
      { key: "developer_token", label: "Developer Token", secret: true },
      { key: "client_id", label: "OAuth Client ID" },
      { key: "client_secret", label: "OAuth Client Secret", secret: true },
      { key: "refresh_token", label: "Refresh Token", secret: true },
      { key: "customer_id", label: "Customer ID", placeholder: "123-456-7890" },
    ],
  },
  webflow: {
    label: "Webflow",
    category: "CMS",
    description: "Publish landing pages to Webflow CMS collections.",
    docsUrl: "https://developers.webflow.com",
    credentialFields: [
      { key: "api_key", label: "Site API Key", secret: true },
      { key: "site_id", label: "Site ID" },
      { key: "collection_id", label: "Collection ID" },
    ],
  },
};

interface GatewayStatusItem {
  provider: string;
  connected: boolean;
  detail: Record<string, unknown>;
  error?: string;
  has_credentials: boolean;
}

interface CredentialRead {
  id: string;
  provider: string;
  label?: string;
  is_active: boolean;
  last_verified_at?: string;
  created_at: string;
  credential_keys: string[];
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function IntegrationsPage() {
  const qc = useQueryClient();
  const [configuringProvider, setConfiguringProvider] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [showHubSpotLists, setShowHubSpotLists] = useState(false);

  const { data: gatewayStatus = [], isLoading: statusLoading } = useQuery<GatewayStatusItem[]>({
    queryKey: ["connectors", "status"],
    queryFn: () => connectors.status(),
    refetchInterval: 30_000,
  });

  const { data: credentials = [] } = useQuery<CredentialRead[]>({
    queryKey: ["connectors", "credentials"],
    queryFn: () => connectors.listCredentials(),
  });

  const { data: hubspotStatus } = useQuery({
    queryKey: ["integrations", "status"],
    queryFn: () => integrations.status(),
  });

  const { data: hubspotLists, isLoading: listsLoading } = useQuery({
    queryKey: ["integrations", "hubspot", "lists"],
    queryFn: () => integrations.hubspotLists(),
    enabled: showHubSpotLists && !!hubspotStatus?.hubspot?.connected,
  });

  const upsertMutation = useMutation({
    mutationFn: (data: unknown) => connectors.upsertCredentials(data),
    onSuccess: () => {
      toast.success("Credentials saved");
      qc.invalidateQueries({ queryKey: ["connectors"] });
      setConfiguringProvider(null);
      setFormValues({});
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Failed to save credentials"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => connectors.deleteCredentials(id),
    onSuccess: () => {
      toast.success("Credentials removed");
      qc.invalidateQueries({ queryKey: ["connectors"] });
    },
  });

  const verifyMutation = useMutation({
    mutationFn: (id: string) => connectors.verifyCredentials(id),
    onSuccess: (data) => {
      toast[data.connected ? "success" : "error"](
        data.connected ? `${data.provider} connected ✓` : `${data.provider}: ${data.error}`
      );
      qc.invalidateQueries({ queryKey: ["connectors"] });
    },
  });

  const statusByProvider = Object.fromEntries(gatewayStatus.map((s) => [s.provider, s]));
  const credByProvider = Object.fromEntries(credentials.map((c) => [c.provider, c]));

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Integrations</h1>
        <p className="text-sm text-muted-foreground mt-1">
          MCP Gateway — configure providers and manage connector credentials.
        </p>
      </div>

      {/* Gateway connector cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(PROVIDER_META).map(([providerKey, meta]) => {
          const s = statusByProvider[providerKey];
          const cred = credByProvider[providerKey];
          const connected = s?.connected ?? false;
          const hasCred = s?.has_credentials ?? !!cred;
          const isConfiguring = configuringProvider === providerKey;

          return (
            <div
              key={providerKey}
              className={cn(
                "rounded-lg border overflow-hidden transition-colors",
                connected ? "border-emerald-200" : "border-border",
              )}
            >
              {/* Header row */}
              <div className={cn("p-4 space-y-2", connected && "bg-emerald-50/30")}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="font-medium text-sm">{meta.label}</span>
                      <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">{meta.category}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">{meta.description}</p>
                    {s?.detail && Object.keys(s.detail).length > 0 && (
                      <p className="text-xs text-emerald-700 mt-0.5">
                        {Object.entries(s.detail).map(([k, v]) => `${k}: ${v}`).join(" · ")}
                      </p>
                    )}
                    {s?.error && !connected && (
                      <p className="text-xs text-red-500 mt-0.5">{s.error}</p>
                    )}
                  </div>
                  <div className="shrink-0 flex items-center gap-2">
                    {statusLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    ) : connected ? (
                      <CheckCircle className="h-4 w-4 text-emerald-600" />
                    ) : (
                      <XCircle className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  {cred && (
                    <>
                      <button
                        onClick={() => verifyMutation.mutate(cred.id)}
                        disabled={verifyMutation.isPending}
                        className="text-xs px-2.5 py-1 rounded-md border border-border hover:bg-accent flex items-center gap-1 disabled:opacity-50"
                      >
                        <ShieldCheck className="h-3 w-3" />
                        Verify
                      </button>
                      <button
                        onClick={() => deleteMutation.mutate(cred.id)}
                        disabled={deleteMutation.isPending}
                        className="text-xs px-2.5 py-1 rounded-md border border-red-200 text-red-600 hover:bg-red-50 flex items-center gap-1 disabled:opacity-50"
                      >
                        <Trash2 className="h-3 w-3" />
                        Remove
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => {
                      setConfiguringProvider(isConfiguring ? null : providerKey);
                      setFormValues({});
                    }}
                    className="text-xs px-2.5 py-1 rounded-md border border-border hover:bg-accent flex items-center gap-1"
                  >
                    <Plus className="h-3 w-3" />
                    {cred ? "Update Keys" : "Configure"}
                  </button>
                  <a
                    href={meta.docsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-auto text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
                  >
                    Docs <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                {cred && (
                  <p className="text-xs text-muted-foreground">
                    Keys stored: {cred.credential_keys.join(", ")}
                    {cred.last_verified_at && ` · Verified ${new Date(cred.last_verified_at).toLocaleDateString()}`}
                  </p>
                )}
              </div>

              {/* Credential form */}
              {isConfiguring && (
                <div className="border-t border-border bg-muted/20 p-4 space-y-3">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Enter credentials for {meta.label}
                  </p>
                  <div className="space-y-2">
                    {meta.credentialFields.map((field) => (
                      <div key={field.key} className="space-y-1">
                        <label className="text-xs text-muted-foreground">{field.label}</label>
                        <input
                          type={field.secret ? "password" : "text"}
                          className="input text-sm w-full font-mono"
                          placeholder={field.placeholder || ""}
                          value={formValues[field.key] || ""}
                          onChange={(e) => setFormValues((prev) => ({ ...prev, [field.key]: e.target.value }))}
                        />
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        const filledFields = Object.fromEntries(
                          Object.entries(formValues).filter(([, v]) => v.trim())
                        );
                        upsertMutation.mutate({
                          provider: providerKey,
                          label: meta.label,
                          credentials: filledFields,
                        });
                      }}
                      disabled={upsertMutation.isPending || Object.values(formValues).every((v) => !v.trim())}
                      className="rounded-md bg-primary text-primary-foreground px-3 py-1.5 text-xs font-medium hover:bg-primary/90 disabled:opacity-50"
                    >
                      {upsertMutation.isPending ? "Saving…" : "Save"}
                    </button>
                    <button
                      onClick={() => { setConfiguringProvider(null); setFormValues({}); }}
                      className="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* HubSpot CRM — separate section (Phase 2 integration) */}
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="p-4 flex items-start justify-between bg-card">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <span className="font-medium text-sm">HubSpot CRM</span>
              <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">CRM</span>
            </div>
            <p className="text-xs text-muted-foreground">Contact lists for email audience targeting. Set via HUBSPOT_ACCESS_TOKEN in .env</p>
            {hubspotStatus?.hubspot?.connected && (
              <p className="text-xs text-emerald-700 mt-0.5">
                Portal: {hubspotStatus.hubspot.hub_domain} (#{hubspotStatus.hubspot.portal_id})
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {hubspotStatus?.hubspot?.connected ? (
              <CheckCircle className="h-4 w-4 text-emerald-600" />
            ) : (
              <XCircle className="h-4 w-4 text-muted-foreground" />
            )}
            {hubspotStatus?.hubspot?.connected && (
              <button
                onClick={() => setShowHubSpotLists(!showHubSpotLists)}
                className="text-xs px-2.5 py-1 rounded-md border border-border hover:bg-accent flex items-center gap-1"
              >
                {showHubSpotLists ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                Lists
              </button>
            )}
          </div>
        </div>

        {showHubSpotLists && (
          <div className="border-t border-border">
            {listsLoading ? (
              <div className="p-4 flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading lists…
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/40">
                    <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">List Name</th>
                    <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">Type</th>
                    <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Contacts</th>
                    <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">List ID</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {hubspotLists?.map((list: any) => (
                    <tr key={list.id} className="hover:bg-muted/20">
                      <td className="px-4 py-2.5 font-medium text-sm">{list.name}</td>
                      <td className="px-4 py-2.5 text-xs text-muted-foreground capitalize">{list.list_type?.toLowerCase()}</td>
                      <td className="px-4 py-2.5 text-sm text-right">{list.size?.toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-xs font-mono text-muted-foreground">{list.id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div className="px-4 py-2 border-t border-border bg-muted/20">
              <p className="text-xs text-muted-foreground">
                Copy a List ID into campaign channel config as <code className="font-mono">hubspot_list_id</code>.
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="rounded-lg border border-dashed border-border p-5 text-center">
        <p className="text-sm text-muted-foreground">
          TikTok Ads, Shopify, and GA4 connectors coming in Phase 4 via the MCP Gateway extension.
        </p>
      </div>
    </div>
  );
}
