import type { ConstructorLayout } from "@/features/constructor/types/constructor";
import type { Skill } from "@/features/skills/types/skill";
import type { ActionDef } from "@/features/actions/types/action";
import type { ToolBinding } from "@/features/tools/types/tool";
import {
  createEmptyAgentWorld,
  type AgentWorld,
} from "@/features/agents/types/world";

export type { Skill } from "@/features/skills/types/skill";
export type { ActionDef } from "@/features/actions/types/action";
export type { ToolBinding } from "@/features/tools/types/tool";
export type { AgentWorld, WorldAddress } from "@/features/agents/types/world";

/** Default avatar when agent.icon is empty. */
export const DEFAULT_AGENT_ICON = "/eva-logo.png";

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
  defaultSkillId?: string;
  skills: Skill[];
  actions: ActionDef[];
  tools: ToolBinding[];
  /** Spatial constructor layout (UI). Wire JSON key remains `constructor`. */
  constructorLayout?: ConstructorLayout;
  /** World axis: addresses hanging on world kinds. */
  world?: AgentWorld;
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
  "skills" | "actions" | "tools" | "constructorLayout" | "world"
> {
  return {
    skills: [],
    actions: [],
    tools: [],
    constructorLayout: { nodes: [] },
    world: createEmptyAgentWorld(),
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
