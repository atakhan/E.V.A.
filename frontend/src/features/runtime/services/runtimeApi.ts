import type {
  AgentMemory,
  AgentPublicationSummary,
  AgentRuntimeSummary,
  RuntimeMetrics,
  RuntimeRunResponse,
  RuntimeSummary,
  SkillRunHistory,
  SkillRunListResponse,
  SkillRunStatusFilter,
} from "@/features/runtime/types/runtime";

import { apiRequest } from "@/shared/api/http";

function statusQueryParam(filter: SkillRunStatusFilter): string | undefined {
  switch (filter) {
    case "active":
      return "running,waiting";
    case "waiting":
      return "waiting";
    case "completed":
      return "completed";
    case "error":
      return "error";
    case "cancelled":
      return "cancelled";
    default:
      return undefined;
  }
}

export async function listPublicationsApi(slug: string): Promise<AgentPublicationSummary[]> {
  const rows = await apiRequest<
    Array<{ id: string; version: string; publishedAt: string; body?: unknown }>
  >(`/agents/${encodeURIComponent(slug)}/publications`);
  return rows.map((row) => ({
    id: row.id,
    version: row.version,
    publishedAt: row.publishedAt,
  }));
}

export async function listSkillRuns(input: {
  agentSlug?: string;
  skillId?: string;
  statusFilter?: SkillRunStatusFilter;
  activeOnly?: boolean;
  limit?: number;
  offset?: number;
}): Promise<SkillRunListResponse> {
  const params = new URLSearchParams();
  if (input.agentSlug) params.set("agentSlug", input.agentSlug);
  if (input.skillId) params.set("skillId", input.skillId);
  if (input.activeOnly) params.set("activeOnly", "true");
  const status = input.statusFilter ? statusQueryParam(input.statusFilter) : undefined;
  if (status) params.set("status", status);
  if (input.limit !== undefined) params.set("limit", String(input.limit));
  if (input.offset !== undefined) params.set("offset", String(input.offset));
  const suffix = params.toString();
  return apiRequest(`/runtime/runs${suffix ? `?${suffix}` : ""}`);
}

export async function getRuntimeSummary(): Promise<RuntimeSummary> {
  return apiRequest("/runtime/summary");
}

export async function getAgentRuntimeSummary(slug: string): Promise<AgentRuntimeSummary> {
  return apiRequest(`/runtime/agents/${encodeURIComponent(slug)}/summary`);
}

export async function getAgentMemory(slug: string): Promise<AgentMemory> {
  return apiRequest(`/runtime/agents/${encodeURIComponent(slug)}/memory`);
}

export async function getRuntimeMetrics(): Promise<RuntimeMetrics> {
  return apiRequest("/runtime/metrics");
}

export async function createRuntimeRun(input: {
  agentSlug: string;
  skillId: string;
  eventType: string;
  payload: Record<string, unknown>;
}): Promise<RuntimeRunResponse> {
  return apiRequest("/runtime/runs", {
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
  return apiRequest("/runtime/events", {
    method: "POST",
    body: JSON.stringify({
      skillRunId: input.skillRunId,
      type: input.eventType,
      payload: input.payload,
    }),
  });
}

export async function getRuntimeRun(runId: string): Promise<RuntimeRunResponse> {
  return apiRequest(`/runtime/runs/${encodeURIComponent(runId)}`);
}

export async function getSkillRunHistory(runId: string): Promise<SkillRunHistory> {
  return apiRequest(`/runtime/runs/${encodeURIComponent(runId)}/history`);
}

export async function cancelSkillRun(runId: string): Promise<{
  ok: boolean;
  skillRunId: string;
  status: string;
  currentState: string;
}> {
  return apiRequest(`/runtime/runs/${encodeURIComponent(runId)}/cancel`, {
    method: "POST",
  });
}
