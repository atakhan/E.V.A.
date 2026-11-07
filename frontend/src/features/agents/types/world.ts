/** Concrete place in a world kind (chat, webhook endpoint, …). */
export interface WorldAddress {
  id: string;
  /** World tool / kind id (e.g. telegram). */
  toolId: string;
  name: string;
  credentialId?: string;
  config?: Record<string, unknown>;
}

export interface AgentWorld {
  addresses: WorldAddress[];
}

export function createEmptyAgentWorld(): AgentWorld {
  return { addresses: [] };
}

export function normalizeAgentWorld(raw: unknown): AgentWorld {
  if (!raw || typeof raw !== "object") return createEmptyAgentWorld();
  const record = raw as Partial<AgentWorld>;
  const addresses = Array.isArray(record.addresses)
    ? record.addresses
        .filter((item): item is WorldAddress => {
          if (!item || typeof item !== "object") return false;
          const address = item as Partial<WorldAddress>;
          return typeof address.id === "string" && typeof address.toolId === "string";
        })
        .map((address) => ({
          id: address.id,
          toolId: address.toolId,
          name: typeof address.name === "string" ? address.name : address.toolId,
          credentialId:
            typeof address.credentialId === "string" ? address.credentialId : undefined,
          config:
            address.config && typeof address.config === "object" && !Array.isArray(address.config)
              ? (address.config as Record<string, unknown>)
              : {},
        }))
    : [];
  return { addresses };
}
