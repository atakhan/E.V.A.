/** Connect policy toward another agent on the Agents channel. */
export interface InteractionPeer {
  agentSlug: string;
  allowInbound: boolean;
  allowOutbound: boolean;
  name?: string;
}

/**
 * Manifesto of how this agent interacts with others.
 * Lives in agent memory; peers hang as addresses on the Agents world channel.
 */
export interface InteractionManifest {
  version: number;
  defaultAllowInbound: boolean;
  defaultAllowOutbound: boolean;
  peers: InteractionPeer[];
}

export interface AgentMemoryDoc {
  interaction: InteractionManifest;
}

export function createEmptyInteractionManifest(): InteractionManifest {
  return {
    version: 1,
    defaultAllowInbound: false,
    defaultAllowOutbound: false,
    peers: [],
  };
}

export function createEmptyAgentMemory(): AgentMemoryDoc {
  return { interaction: createEmptyInteractionManifest() };
}

function asBool(value: unknown, fallback: boolean): boolean {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (normalized === "true" || normalized === "1" || normalized === "yes") return true;
    if (normalized === "false" || normalized === "0" || normalized === "no") return false;
  }
  return fallback;
}

export function normalizeInteractionManifest(raw: unknown): InteractionManifest {
  const empty = createEmptyInteractionManifest();
  if (!raw || typeof raw !== "object") return empty;
  const record = raw as Partial<InteractionManifest> & {
    defaultAllowInbound?: unknown;
    defaultAllowOutbound?: unknown;
  };
  const peers: InteractionPeer[] = [];
  const seen = new Set<string>();
  for (const item of Array.isArray(record.peers) ? record.peers : []) {
    if (!item || typeof item !== "object") continue;
    const peer = item as Partial<InteractionPeer>;
    const agentSlug = typeof peer.agentSlug === "string" ? peer.agentSlug.trim() : "";
    if (!agentSlug || seen.has(agentSlug)) continue;
    seen.add(agentSlug);
    peers.push({
      agentSlug,
      allowInbound: asBool(peer.allowInbound, true),
      allowOutbound: asBool(peer.allowOutbound, true),
      name: typeof peer.name === "string" ? peer.name : undefined,
    });
  }
  return {
    version: typeof record.version === "number" ? record.version : 1,
    defaultAllowInbound: asBool(record.defaultAllowInbound, false),
    defaultAllowOutbound: asBool(record.defaultAllowOutbound, false),
    peers,
  };
}

export function normalizeAgentMemory(raw: unknown): AgentMemoryDoc {
  if (!raw || typeof raw !== "object") return createEmptyAgentMemory();
  const record = raw as Partial<AgentMemoryDoc>;
  return { interaction: normalizeInteractionManifest(record.interaction) };
}
