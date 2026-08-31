export interface ToolCredential {
  id: string;
  toolId: string;
  name: string;
  meta: {
    bot_username?: string;
    bot_id?: number;
    bot_name?: string;
    verified?: boolean;
    balance_amount?: string;
    provider?: string;
    backend_base_url?: string;
    health_status?: number;
    latency_ms?: number;
  };
  oneTimeSecrets?: {
    inboundApiKey?: string;
  };
  createdAt: string;
  updatedAt: string;
}

export interface PolzaModel {
  id: string;
  name: string;
  type: string;
  contextLength?: number | null;
}

import { fetchAgentToolLogs } from "@/features/tools/services/toolLogsApi";

export interface PolzaApiLog {
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

/** @deprecated Use fetchAgentToolLogs from toolLogsApi */
export async function fetchPolzaLogs(
  agentSlug: string,
  options?: { credentialId?: string; limit?: number },
): Promise<PolzaApiLog[]> {
  const page = await fetchAgentToolLogs(agentSlug, {
    toolId: "polza_ai_llm",
    credentialId: options?.credentialId,
    limit: options?.limit ?? 50,
  });
  return page.items;
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
  input:
    | { toolId: "telegram"; name: string; botToken: string }
    | { toolId: "polza_ai_llm"; name: string; apiKey: string }
    | {
        toolId: "web_client";
        name: string;
        backendBaseUrl: string;
        outboundApiKey: string;
        inboundApiKey?: string;
      },
): Promise<ToolCredential> {
  let secret: Record<string, string>;
  if (input.toolId === "telegram") {
    secret = { bot_token: input.botToken };
  } else if (input.toolId === "polza_ai_llm") {
    secret = { api_key: input.apiKey };
  } else {
    secret = {
      backend_base_url: input.backendBaseUrl.trim(),
      outbound_api_key: input.outboundApiKey.trim(),
    };
    if (input.inboundApiKey?.trim()) {
      secret.inbound_api_key = input.inboundApiKey.trim();
    }
  }

  return request(`/agents/${encodeURIComponent(agentSlug)}/credentials`, {
    method: "POST",
    body: JSON.stringify({
      toolId: input.toolId,
      name: input.name,
      secret,
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

export async function fetchPolzaModels(
  agentSlug: string,
  credentialId?: string,
): Promise<PolzaModel[]> {
  const query = credentialId ? `?credentialId=${encodeURIComponent(credentialId)}` : "";
  return request(`/agents/${encodeURIComponent(agentSlug)}/tools/polza_ai_llm/models${query}`);
}

export async function fetchPolzaBalance(
  agentSlug: string,
  credentialId?: string,
): Promise<{ amount: string; credentialId: string }> {
  const query = credentialId ? `?credentialId=${encodeURIComponent(credentialId)}` : "";
  return request(`/agents/${encodeURIComponent(agentSlug)}/tools/polza_ai_llm/balance${query}`);
}
