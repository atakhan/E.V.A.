import type {
  AgentPublicationSummary,
  RuntimeRunResponse,
} from "@/features/runtime/types/runtime";

const API_BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    let detail = await response.text();
    try {
      const parsed = JSON.parse(detail) as { detail?: string };
      if (typeof parsed.detail === "string") {
        detail = parsed.detail;
      }
    } catch {
      // keep raw text
    }
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function listPublicationsApi(slug: string): Promise<AgentPublicationSummary[]> {
  const rows = await request<
    Array<{ id: string; version: string; publishedAt: string; body?: unknown }>
  >(`/agents/${encodeURIComponent(slug)}/publications`);
  return rows.map((row) => ({
    id: row.id,
    version: row.version,
    publishedAt: row.publishedAt,
  }));
}

export async function createRuntimeRun(input: {
  agentSlug: string;
  skillId: string;
  eventType: string;
  payload: Record<string, unknown>;
}): Promise<RuntimeRunResponse> {
  return request("/runtime/runs", {
    method: "POST",
    body: JSON.stringify({
      agentSlug: input.agentSlug,
      skillId: input.skillId,
      event: {
        type: input.eventType,
        payload: input.payload,
      },
    }),
  });
}

export async function postRuntimeEvent(input: {
  skillRunId: string;
  eventType: string;
  payload: Record<string, unknown>;
}): Promise<RuntimeRunResponse> {
  return request("/runtime/events", {
    method: "POST",
    body: JSON.stringify({
      skillRunId: input.skillRunId,
      type: input.eventType,
      payload: input.payload,
    }),
  });
}

export async function getRuntimeRun(runId: string): Promise<RuntimeRunResponse> {
  return request(`/runtime/runs/${encodeURIComponent(runId)}`);
}
