import type {
  AttackFamily, AttackLabRunResponse, AttackLabRun,
  WAFInspectResponse, Policy, RequestEvent, StatsSummary,
  Session, EndpointProfile, BatchRunResponse, BatchRun,
  ModelInfo, EvaluationRunResponse,
} from "@/types/api";

const API_BASE = "/api/backend";

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    cache: "no-store",
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const api = {
  // WAF
  waf: {
    inspect: (request: any) =>
      fetchApi<WAFInspectResponse>("/waf/inspect", {
        method: "POST",
        body: JSON.stringify(request),
      }),

    inspectAndProxy: (request: any) =>
      fetchApi<WAFInspectResponse>("/waf/inspect-and-proxy", {
        method: "POST",
        body: JSON.stringify(request),
      }),

    getMode: () => fetchApi<{ mode: string }>("/waf/mode"),
    setMode: (mode: string) =>
      fetchApi<{ mode: string; message?: string }>(`/waf/mode?mode=${encodeURIComponent(mode)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      }),

    getPolicy: () => fetchApi<Policy>("/waf/policy"),
    updatePolicy: (policy: any) =>
      fetchApi<Policy>("/waf/policy", { method: "PUT", body: JSON.stringify(policy) }),

    submitFeedback: (feedback: any) =>
      fetchApi<void>("/waf/feedback", { method: "POST", body: JSON.stringify(feedback) }),

    getEvents: (params?: {
      limit?: number;
      offset?: number;
      decision?: string;
      attack_type?: string;
      source_ip?: string;
      session_id?: string;
    }) => {
      const search = new URLSearchParams();
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          if (v !== undefined) search.set(k, String(v));
        });
      }
      return fetchApi<RequestEvent[]>(`/waf/events?${search}`);
    },

    getEvent: (requestId: string) => fetchApi<RequestEvent>(`/waf/events/${requestId}`),
    getEventExplanation: (requestId: string) => fetchApi<unknown>(`/waf/events/${requestId}/explanation`),
    getStats: () => fetchApi<unknown>("/waf/stats"),
    health: () => fetchApi<unknown>("/waf/health"),
  },

  // Events
  events: {
    getRecent: (limit = 50) => fetchApi<RequestEvent[]>(`/events/recent?limit=${limit}`),
    getThreats: (limit = 50, severity?: string) => {
      const search = new URLSearchParams({ limit: String(limit) });
      if (severity) search.set("severity", severity);
      return fetchApi<RequestEvent[]>(`/events/threats?${search}`);
    },
    getSummary: () => fetchApi<StatsSummary>("/events/stats/summary"),
    getSessions: (limit = 50, minRisk = 0) =>
      fetchApi<Session[]>(`/events/sessions?limit=${limit}&min_risk=${minRisk}`),
    getSession: (sessionId: string) => fetchApi<Session>(`/events/sessions/${sessionId}`),
    getSessionEvents: (sessionId: string, limit = 100) =>
      fetchApi<RequestEvent[]>(`/events/sessions/${sessionId}/events?limit=${limit}`),
    getCampaigns: (limit = 50, status?: string) => {
      const search = new URLSearchParams({ limit: String(limit) });
      if (status) search.set("status", status);
      return fetchApi<unknown[]>(`/events/campaigns?${search}`);
    },
  },

  // Context
  context: {
    importOpenAPI: (spec: any, source = "json", baseUrl?: string) =>
      fetchApi("/context/openapi/import", {
        method: "POST",
        body: JSON.stringify({ spec, source, base_url: baseUrl }),
      }),
    importOpenAPIFile: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return fetch(`${API_BASE}/context/openapi/import/file`, {
        method: "POST",
        body: form,
      }).then((r) => r.json());
    },
    getEndpoints: () => fetchApi<EndpointProfile[]>("/context/endpoints"),
    getEndpointsSummary: () => fetchApi<unknown>("/context/endpoints/summary"),
    getEndpoint: (id: number) => fetchApi<EndpointProfile>(`/context/endpoints/${id}`),
    updateSensitivity: (id: number, sensitivity: string) =>
      fetchApi<void>(`/context/endpoints/${id}/sensitivity`, {
        method: "POST",
        body: JSON.stringify({ sensitivity }),
      }),
  },

  // Attack Lab
  attackLab: {
    run: (config: {
      attack_family: string;
      base_payloads?: string[];
      variant_count: number;
      target_endpoint: string;
    }) => fetchApi<AttackLabRunResponse>("/attack-lab/run", { method: "POST", body: JSON.stringify(config) }),
    getRun: (runId: string) => fetchApi<AttackLabRun>(`/attack-lab/runs/${runId}`),
    listRuns: () => fetchApi<AttackLabRun[]>("/attack-lab/runs"),
    getFamilies: () => fetchApi<{ families: AttackFamily[] }>("/attack-lab/payloads/families"),
  },

  // Batch
  batch: {
    analyze: (file: File, hasLabels = false) => {
      const form = new FormData();
      form.append("file", file);
      form.append("has_labels", String(hasLabels));
      return fetch(`${API_BASE}/batch/analyze`, {
        method: "POST",
        body: form,
      }).then((r) => r.json());
    },
    getRun: (runId: string) => fetchApi<BatchRunResponse>(`/batch/runs/${runId}`),
    listRuns: () => fetchApi<BatchRun[]>("/batch/runs"),
    exportResults: (runId: string, format = "json") =>
      fetch(`${API_BASE}/batch/runs/${runId}/export?format=${format}`).then((r) => r.json()),
  },

  // Models
  models: {
    list: () => fetchApi<ModelInfo[]>("/models"),
    getActive: () => fetchApi<ModelInfo>("/models/active"),
    get: (id: number) => fetchApi<ModelInfo>(`/models/${id}`),
    activate: (id: number) => fetchApi<void>(`/models/${id}/activate`, { method: "POST" }),
    getCurrentInfo: () => fetchApi<unknown>("/models/info/current"),
    evaluate: (datasetName = "test", runName?: string) =>
      fetchApi<EvaluationRunResponse>("/models/evaluate", {
        method: "POST",
        body: JSON.stringify({ dataset_name: datasetName, run_name: runName }),
      }),
    listEvaluations: () => fetchApi<EvaluationRunResponse[]>("/models/evaluation/runs"),
    getEvaluation: (id: number) => fetchApi<EvaluationRunResponse>(`/models/evaluation/runs/${id}`),
  },
};