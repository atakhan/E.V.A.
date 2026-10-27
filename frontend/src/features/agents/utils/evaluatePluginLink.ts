import type { Agent } from "@/features/agents/types/agent";
import { toolUsage } from "@/features/agents/utils/agentDependencies";
import type { WorldLinkEvaluation } from "@/features/agents/utils/evaluateWorldLink";
import { getToolDefinition, isToolImplemented } from "@/features/tools/registry/builtinTools";
import type { ToolInstance } from "@/features/tools/types/tool";

/**
 * Traffic light for a plugin (non-world tool instance) on the constructor table.
 * Red mirrors server validation errors; color is derived, not stored.
 * A plugin no action calls yet stays green: plugins connect independently of skills (axiom 10).
 */
export function evaluatePluginLink(agent: Agent, instance: ToolInstance): WorldLinkEvaluation {
  const def = getToolDefinition(instance.toolId);
  if (!def) {
    return { status: "red", reason: "Тип плагина не найден в каталоге", instanceId: instance.id };
  }
  if (!instance.enabled) {
    return { status: "off", reason: "Плагин выключен", instanceId: instance.id };
  }
  if (!isToolImplemented(def)) {
    return {
      status: "red",
      reason: "Нет реализации в runtime — с ним агент не опубликуется",
      instanceId: instance.id,
    };
  }
  if (def.credentialKind && !instance.credentialId?.trim()) {
    return { status: "red", reason: "Нет credential", instanceId: instance.id };
  }
  if (toolUsage(agent, { kind: "instance", instanceId: instance.id }).actions.length === 0) {
    return {
      status: "green",
      reason: "Плагин готов, Actions агента его пока не вызывают",
      instanceId: instance.id,
    };
  }
  return { status: "green", reason: "Плагин готов", instanceId: instance.id };
}
