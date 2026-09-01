import type { Skill } from "@/features/skills/types/skill";
import type { ActionDef } from "@/features/actions/types/action";
import type { ToolBinding } from "@/features/tools/types/tool";

export type { Skill } from "@/features/skills/types/skill";
export type { ActionDef } from "@/features/actions/types/action";
export type { ToolBinding } from "@/features/tools/types/tool";

export interface Agent {
  id: string;
  slug: string;
  name: string;
  description: string;
  createdAt: string;
  updatedAt: string;
  archivedAt?: string | null;
  skills: Skill[];
  actions: ActionDef[];
  tools: ToolBinding[];
}

export type AgentInput = {
  name: string;
  slug: string;
  description?: string;
};

export type AgentMutationResult =
  | { ok: true; agent: Agent }
  | { ok: false; error: string };

export function createEmptyAgentBody(): Pick<Agent, "skills" | "actions" | "tools"> {
  return {
    skills: [],
    actions: [],
    tools: [],
  };
}
