import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach token from localStorage on every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("emp_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("emp_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// ── Campaigns ──────────────────────────────────────────────────────────────
export const campaigns = {
  list: (params?: { status?: string; page?: number; page_size?: number }) =>
    api.get("/api/campaigns", { params }).then((r) => r.data),
  get: (id: string) => api.get(`/api/campaigns/${id}`).then((r) => r.data),
  create: (data: unknown) => api.post("/api/campaigns", data).then((r) => r.data),
  update: (id: string, data: unknown) =>
    api.patch(`/api/campaigns/${id}`, data).then((r) => r.data),
};

// ── Content ────────────────────────────────────────────────────────────────
export const content = {
  generate: (data: unknown) => api.post("/api/content/generate", data).then((r) => r.data),
  listByCampaign: (campaignId: string) =>
    api.get(`/api/content/campaign/${campaignId}`).then((r) => r.data),
  get: (assetId: string) => api.get(`/api/content/${assetId}`).then((r) => r.data),
  rewrite: (id: string, data: unknown) =>
    api.post(`/api/content/${id}/rewrite`, data).then((r) => r.data),
  submit: (id: string) => api.post(`/api/content/${id}/submit`).then((r) => r.data),
};

// ── Approvals ──────────────────────────────────────────────────────────────
export const approvals = {
  list: (params?: { status?: string; page?: number }) =>
    api.get("/api/approvals", { params }).then((r) => r.data),
  create: (data: unknown) => api.post("/api/approvals", data).then((r) => r.data),
  decide: (id: string, data: unknown) =>
    api.post(`/api/approvals/${id}/decision`, data).then((r) => r.data),
  comment: (id: string, data: unknown) =>
    api.post(`/api/approvals/${id}/comments`, data).then((r) => r.data),
};

// ── Voice Packs ────────────────────────────────────────────────────────────
export const voicePacks = {
  list: () => api.get("/api/voice-packs").then((r) => r.data),
  create: (data: unknown) => api.post("/api/voice-packs", data).then((r) => r.data),
  update: (id: string, data: unknown) =>
    api.patch(`/api/voice-packs/${id}`, data).then((r) => r.data),
  ingest: (id: string, data: unknown) =>
    api.post(`/api/voice-packs/${id}/ingest`, data).then((r) => r.data),
};

// ── Executions ─────────────────────────────────────────────────────────────
export const executions = {
  listByCampaign: (campaignId: string) =>
    api.get(`/api/executions/campaign/${campaignId}`).then((r) => r.data),
  run: (data: unknown) => api.post("/api/executions/run", data).then((r) => r.data),
  retry: (runId: string) => api.post(`/api/executions/${runId}/retry`).then((r) => r.data),
};

// ── Experiments ────────────────────────────────────────────────────────────
export const experiments = {
  create: (data: unknown) => api.post("/api/experiments", data).then((r) => r.data),
  listByCampaign: (campaignId: string) =>
    api.get(`/api/experiments/campaign/${campaignId}`).then((r) => r.data),
  get: (id: string) => api.get(`/api/experiments/${id}`).then((r) => r.data),
  update: (id: string, data: unknown) => api.patch(`/api/experiments/${id}`, data).then((r) => r.data),
  setWeights: (id: string, weights: Record<string, number>) =>
    api.post(`/api/experiments/${id}/set-weights`, { weights }).then((r) => r.data),
  selectVariant: (id: string) =>
    api.post(`/api/experiments/${id}/select-variant`).then((r) => r.data),
  recordEvent: (id: string, data: unknown) =>
    api.post(`/api/experiments/${id}/record-event`, data).then((r) => r.data),
  conclude: (id: string, data: unknown) =>
    api.post(`/api/experiments/${id}/conclude`, data).then((r) => r.data),
};

// ── Integrations ───────────────────────────────────────────────────────────
export const integrations = {
  status: () => api.get("/api/integrations/status").then((r) => r.data),
  hubspotLists: () => api.get("/api/integrations/hubspot/lists").then((r) => r.data),
};

// ── Connectors (MCP Gateway) ────────────────────────────────────────────────
export const connectors = {
  status: () => api.get("/api/connectors/status").then((r) => r.data),
  listCredentials: () => api.get("/api/connectors/credentials").then((r) => r.data),
  upsertCredentials: (data: unknown) =>
    api.post("/api/connectors/credentials", data).then((r) => r.data),
  deleteCredentials: (id: string) =>
    api.delete(`/api/connectors/credentials/${id}`).then((r) => r.data),
  verifyCredentials: (id: string) =>
    api.post(`/api/connectors/credentials/${id}/verify`).then((r) => r.data),
  listJobs: (params?: { campaign_id?: string; provider?: string; limit?: number }) =>
    api.get("/api/connectors/jobs", { params }).then((r) => r.data),
  getJob: (id: string) => api.get(`/api/connectors/jobs/${id}`).then((r) => r.data),
};

// ── Analytics ──────────────────────────────────────────────────────────────
export const analytics = {
  summary: (params?: { campaign_id?: string }) =>
    api.get("/api/analytics/summary", { params }).then((r) => r.data),
};

// ── Audit ──────────────────────────────────────────────────────────────────
export const auditLogs = {
  list: (params?: { action?: string; resource_type?: string; page?: number }) =>
    api.get("/api/audit-logs", { params }).then((r) => r.data),
};

// ── Auth ───────────────────────────────────────────────────────────────────
export const auth = {
  login: (data: { email: string; password: string; tenant_slug: string }) =>
    api.post("/api/auth/token", data).then((r) => r.data),
};
