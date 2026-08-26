export interface ToolCredential {
  id: string;
  toolId: string;
  name: string;
  meta: {
    bot_username?: string;
    bot_id?: number;
    bot_name?: string;
  };
  createdAt: string;
  updatedAt: string;
}

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

export async function fetchCredentials(agentSlug: string, toolId?: string): Promise<ToolCredential[]> {
  const query = toolId ? `?tool_id=${encodeURIComponent(toolId)}` : "";
  return request(`/agents/${encodeURIComponent(agentSlug)}/credentials${query}`);
}

export async function createCredential(
  agentSlug: string,
  input: { toolId: string; name: string; botToken: string },
): Promise<ToolCredential> {
  return request(`/agents/${encodeURIComponent(agentSlug)}/credentials`, {
    method: "POST",
    body: JSON.stringify({
      toolId: input.toolId,
      name: input.name,
      secret: { bot_token: input.botToken },
    }),
  });
}

export async function verifyCredential(agentSlug: string, credentialId: string): Promise<ToolCredential> {
  return request(
    `/agents/${encodeURIComponent(agentSlug)}/credentials/${encodeURIComponent(credentialId)}/verify`,
    { method: "POST" },
  );
}

export async function deleteCredential(agentSlug: string, credentialId: string): Promise<void> {
  await request(`/agents/${encodeURIComponent(agentSlug)}/credentials/${encodeURIComponent(credentialId)}`, {
    method: "DELETE",
  });
}

export async function setTelegramWebhook(agentSlug: string, credentialId: string): Promise<{ ok: boolean; url: string }> {
  return request(
    `/agents/${encodeURIComponent(agentSlug)}/credentials/${encodeURIComponent(credentialId)}/set-webhook`,
    { method: "POST" },
  );
}
