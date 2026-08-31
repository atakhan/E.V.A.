import type { Agent } from "@/features/agents/types/agent";
import type { ToolInstance } from "@/features/tools/types/tool";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";

export type ResolveToolStatus = "ok" | "unknown" | "ambiguous" | "disabled";

export interface ResolvedToolInstance {
  instanceId: string;
  typeId: string;
  instance: ToolInstance | null;
  status: ResolveToolStatus;
}

export function listToolInstances(agent: Pick<Agent, "tools">): ToolInstance[] {
  return agent.tools;
}

export function enabledInstances(agent: Pick<Agent, "tools">): ToolInstance[] {
  return agent.tools.filter((item) => item.enabled);
}

export function instancesByType(
  agent: Pick<Agent, "tools">,
  typeId: string,
  enabledOnly = false,
): ToolInstance[] {
  const items = enabledOnly ? enabledInstances(agent) : agent.tools;
  return items.filter((item) => item.toolId === typeId);
}

export function findInstanceById(
  agent: Pick<Agent, "tools">,
  instanceId: string,
): ToolInstance | undefined {
  return agent.tools.find((item) => item.id === instanceId);
}

export function resolveRecipeTool(
  agent: Pick<Agent, "tools">,
  toolRef: string,
): ResolvedToolInstance {
  const ref = toolRef.trim();
  if (!ref) {
    return { instanceId: "", typeId: "", instance: null, status: "unknown" };
  }

  const byId = findInstanceById(agent, ref);
  if (byId) {
    return {
      instanceId: byId.id,
      typeId: byId.toolId,
      instance: byId,
      status: byId.enabled ? "ok" : "disabled",
    };
  }

  if (!getToolDefinition(ref)) {
    return { instanceId: ref, typeId: ref, instance: null, status: "unknown" };
  }

  const enabled = instancesByType(agent, ref, true);
  if (enabled.length === 1) {
    const item = enabled[0]!;
    return { instanceId: item.id, typeId: item.toolId, instance: item, status: "ok" };
  }
  if (enabled.length > 1) {
    return { instanceId: ref, typeId: ref, instance: null, status: "ambiguous" };
  }

  const any = instancesByType(agent, ref, false);
  if (any.length === 1 && !any[0]!.enabled) {
    const item = any[0]!;
    return { instanceId: item.id, typeId: item.toolId, instance: item, status: "disabled" };
  }

  return { instanceId: ref, typeId: ref, instance: null, status: "unknown" };
}

export function instanceLabel(instance: ToolInstance): string {
  return `${instance.name} (${instance.toolId})`;
}