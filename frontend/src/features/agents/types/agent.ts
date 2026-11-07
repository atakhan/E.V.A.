import type { ConstructorLayout } from "@/features/constructor/types/constructor";
import type { Skill } from "@/features/skills/types/skill";
import type { ActionDef } from "@/features/actions/types/action";
import type { ToolBinding } from "@/features/tools/types/tool";
import {
  createEmptyAgentMemory,
  type AgentMemoryDoc,
} from "@/features/agents/types/memory";
import {
  createEmptyAgentWorld,
  type AgentWorld,
} from "@/features/agents/types/world";

export type { Skill } from "@/features/skills/types/skill";
export type { ActionDef } from "@/features/actions/types/action";
export type { ToolBinding } from "@/features/tools/types/tool";
export type { AgentWorld, WorldAddress } from "@/features/agents/types/world";
export type {
  AgentMemoryDoc,
  InteractionManifest,
  InteractionPeer,
} from "@/features/agents/types/memory";

/** Default avatar when agent.icon is empty. */
export const DEFAULT_AGENT_ICON = "/eva-logo.png";

export type AgentKind = "library" | "runtime" | "fork" | "platform";

/** Platform agent that runs the projects desk. */
export const EVA_AGENT_SLUG = "eva";

export interface Agent {
  id: string;
  slug: string;
  name: string;
  description: string;
  /** Avatar URL or data URL; empty → DEFAULT_AGENT_ICON. */
  icon: string;
  createdAt: string;
  updatedAt: string;
  archivedAt?: string | null;
  /** `runtime` — project system agent; `fork` — project copy of a library agent; `platform` — Eva. */
  kind?: AgentKind;
  /** Set on the project runtime agent and on a project fork. */
  projectSlug?: string;
  /** Library agent this fork was copied from. */
  originSlug?: string;
  defaultSkillId?: string;
  skills: Skill[];
  actions: ActionDef[];
  tools: ToolBinding[];
  /** Spatial constructor layout (UI). Wire JSON key remains `constructor`. */
  constructorLayout?: ConstructorLayout;
  /** World axis: addresses hanging on world kinds. */
  world?: AgentWorld;
  /** Durable agent memory; includes interaction manifesto with other agents. */
  memory?: AgentMemoryDoc;
}

export type AgentInput = {
  name: string;
  slug: string;
  description?: string;
  icon?: string;
};

export function agentIconSrc(agent: Pick<Agent, "icon"> | { icon?: string | null }): string {
  const icon = agent.icon?.trim();
  return icon || DEFAULT_AGENT_ICON;
}

export type AgentMutationResult =
  | { ok: true; agent: Agent }
  | { ok: false; error: string };

export function createEmptyAgentBody(): Pick<
  Agent,
  "skills" | "actions" | "tools" | "constructorLayout" | "world" | "memory"
> {
  return {
    skills: [],
    actions: [],
    tools: [],
    constructorLayout: { nodes: [] },
    world: createEmptyAgentWorld(),
    memory: createEmptyAgentMemory(),
  };
}

/** Map in-memory Agent to API/wire JSON (`constructorLayout` → `constructor`). */
export function agentToWire(agent: Agent): Record<string, unknown> {
  const { constructorLayout, ...rest } = agent;
  return {
    ...rest,
    constructor: constructorLayout ?? { nodes: [] },
  };
}
