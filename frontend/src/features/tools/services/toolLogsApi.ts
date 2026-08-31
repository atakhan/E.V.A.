export interface ToolApiLog {
  id: string;
  toolId: string;
  credentialId?: string | null;
  command: string;
  model?: string | null;
  status: string;
  requestSummary: Record<string, unknown>;
  responseSummary: Record<string, unknown>;
  usage: Record<string, unknown>;
  durationMs?: number | null;
  errorMessage?: string | null;
  skillRunId?: string | null;
  actionId?: string | null;
  createdAt: string;
}

export interface ToolLogPage {
  items: ToolApiLog[];
  total: number;
  limit: number;
  offset: number;
}

export interface ToolLogStats {
  total: number;
  ok: number;
  error: number;
  avgDurationMs: number | null;
  byTool: Array<{
    toolId: string;
    count: number;
    avgDurationMs: number | null;
    errors: number;
  }>;
  byCommand: Array<{
    toolId: string;
    command: string;
    count: number;
  }>;
  usageTotals: Record<string, number>;
  windowHours: number | null;
}

export interface ToolLogQuery {
  toolId?: string;
  credentialId?: string;
  command?: string;
  status?: string;
  skillRunId?: string;
  limit?: number;
  offset?: number;
}

const API_BASE = "/api";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function fetchAgentToolLogs(
  agentSlug: string,
  query: ToolLogQuery = {},
): Promise<ToolLogPage> {
  const params = new URLSearchParams();
  if (query.toolId) params.set("toolId", query.toolId);
  if (query.credentialId) params.set("credentialId", query.credentialId);
  if (query.command) params.set("command", query.command);
  if (query.status) params.set("status", query.status);
  if (query.skillRunId) params.set("skillRunId", query.skillRunId);
  if (query.limit) params.set("limit", String(query.limit));
  if (query.offset) params.set("offset", String(query.offset));
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request(`/agents/${encodeURIComponent(agentSlug)}/tool-logs${suffix}`);
}

export async function fetchAgentToolLogStats(
  agentSlug: string,
  query: { toolId?: string; credentialId?: string; skillRunId?: string; hours?: number } = {},
): Promise<ToolLogStats> {
  const params = new URLSearchParams();
  if (query.toolId) params.set("toolId", query.toolId);
  if (query.credentialId) params.set("credentialId", query.credentialId);
  if (query.skillRunId) params.set("skillRunId", query.skillRunId);
  if (query.hours) params.set("hours", String(query.hours));
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request(`/agents/${encodeURIComponent(agentSlug)}/tool-logs/stats${suffix}`);
}

/** Fetch all pages up to `max` records (for export). */
export async function fetchAllAgentToolLogs(
  agentSlug: string,
  query: ToolLogQuery = {},
  max = 2000,
): Promise<ToolApiLog[]> {
  const collected: ToolApiLog[] = [];
  const pageSize = 200;
  let offset = 0;

  while (collected.length < max) {
    const page = await fetchAgentToolLogs(agentSlug, {
      ...query,
      limit: pageSize,
      offset,
    });
    collected.push(...page.items);
    if (page.items.length === 0 || collected.length >= page.total) {
      break;
    }
    offset += page.items.length;
  }

  return collected.slice(0, max);
}
