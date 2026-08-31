import type { Agent } from "@/features/agents/types/agent";
import type { AgentValidationReport } from "@/features/agents/utils/validateAgent";

const API_BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `HTTP ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function fetchAgentsList(options?: {
  includeArchived?: boolean;
}): Promise<
  Pick<Agent, "id" | "slug" | "name" | "description" | "createdAt" | "updatedAt" | "archivedAt">[]
> {
  const params = new URLSearchParams();
  if (options?.includeArchived) {
    params.set("includeArchived", "true");
  }
  const query = params.toString();
  return request(`/agents${query ? `?${query}` : ""}`);
}

export async function fetchAgent(slug: string): Promise<Agent> {
  return request(`/agents/${encodeURIComponent(slug)}`);
}

export async function createAgentApi(input: {
  name: string;
  slug: string;
  description?: string;
}): Promise<Agent> {
  return request("/agents", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function saveAgentApi(agent: Agent): Promise<Agent> {
  return request(`/agents/${encodeURIComponent(agent.slug)}`, {
    method: "PUT",
    body: JSON.stringify(agent),
  });
}

export async function deleteAgentApi(slug: string): Promise<void> {
  await request(`/agents/${encodeURIComponent(slug)}`, { method: "DELETE" });
}

export async function archiveAgentApi(slug: string): Promise<{ slug: string; archivedAt: string }> {
  return request(`/agents/${encodeURIComponent(slug)}/archive`, { method: "POST" });
}

export async function unarchiveAgentApi(slug: string): Promise<{ slug: string; archivedAt: string | null }> {
  return request(`/agents/${encodeURIComponent(slug)}/unarchive`, { method: "POST" });
}

export async function validateAgentApi(slug: string): Promise<AgentValidationReport> {
  return request(`/agents/${encodeURIComponent(slug)}/validate`, { method: "POST" });
}

export async function publishAgentApi(slug: string): Promise<{ version: string; publicationId: string }> {
  return request(`/agents/${encodeURIComponent(slug)}/publish`, { method: "POST" });
}

export async function checkApiHealth(): Promise<boolean> {
  try {
    const response = await fetch("/health");
    if (!response.ok) return false;
    const body = (await response.json()) as { ok?: boolean };
    return body.ok === true;
  } catch {
    return false;
  }
}
