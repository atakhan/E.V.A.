export interface ToolCommandDef {
  id: string;
  description: string;
}

export interface ToolEventDef {
  id: string;
  description: string;
}

/** Static tool capability available in the constructor catalog. */
export interface ToolDefinition {
  id: string;
  name: string;
  description: string;
  commands: ToolCommandDef[];
  events: ToolEventDef[];
  /** Optional lifecycle states — not every tool has them. */
  states: string[];
}

/** Per-agent binding to a catalog tool. */
export interface ToolBinding {
  id: string;
  toolId: string;
  enabled: boolean;
  /** Reference to backend tool_credentials.id */
  credentialId?: string;
  /** Free-form non-secret config notes. */
  configNote: string;
}

export type ToolMutationResult =
  | { ok: true; binding: ToolBinding }
  | { ok: false; error: string };
