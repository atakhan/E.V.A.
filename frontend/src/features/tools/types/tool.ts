export interface ToolCommandDef {
  id: string;
  description: string;
}

export interface ToolEventDef {
  id: string;
  description: string;
}

export type ToolConfigFieldType = "string" | "integer" | "boolean" | "enum";

export interface ToolConfigFieldDef {
  id: string;
  type: ToolConfigFieldType;
  required?: boolean;
  default?: unknown;
  scope?: "instance" | "call";
  enum?: string[];
  ui?: { label?: string; group?: string };
}

export type CredentialPolicy = "unique_per_instance" | "shared_allowed";

/** Static tool type in the global library catalog. */
export interface ToolDefinition {
  id: string;
  name: string;
  description: string;
  commands: ToolCommandDef[];
  events: ToolEventDef[];
  states: string[];
  configSchema?: ToolConfigFieldDef[];
  credentialKind?: string;
  credentialPolicy?: CredentialPolicy;
}

/** Per-agent instance of a catalog tool type. */
export interface ToolInstance {
  id: string;
  toolId: string;
  name: string;
  enabled: boolean;
  credentialId?: string;
  config: Record<string, unknown>;
  /** @deprecated use config */
  configNote?: string;
}

/** @deprecated use ToolInstance */
export type ToolBinding = ToolInstance;

export type ToolMutationResult =
  | { ok: true; instance: ToolInstance }
  | { ok: false; error: string };
