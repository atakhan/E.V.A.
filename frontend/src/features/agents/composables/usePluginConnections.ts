import { computed } from "vue";
import {
  getAgentBySlug,
  replaceAgent,
  touchAgent,
} from "@/features/agents/services/agentsStorage";
import type { Agent } from "@/features/agents/types/agent";
import { evaluatePluginLink } from "@/features/agents/utils/evaluatePluginLink";
import {
  getBuiltinTools,
  getToolDefinition,
  isToolImplemented,
} from "@/features/tools/registry/builtinTools";
import { createToolInstance } from "@/features/tools/types/normalize";
import { mergeConfigDefaults } from "@/features/tools/utils/instanceConfig";

function freeInstanceId(agent: Agent, typeId: string): string {
  const taken = new Set(agent.tools.map((tool) => tool.id));
  if (!taken.has(typeId)) return typeId;
  let n = 2;
  while (taken.has(`${typeId}_${n}`)) n += 1;
  return `${typeId}_${n}`;
}

/** Plugins = enabled instances of non-world tools (bottom zone of the constructor). */
export function usePluginConnections(agentSlug: () => string) {
  const agent = computed(() => getAgentBySlug(agentSlug()));

  const pluginTools = computed(() => getBuiltinTools().filter((tool) => !tool.world));

  const pluginInstances = computed(() =>
    (agent.value?.tools ?? []).filter(
      (tool) => tool.enabled && !getToolDefinition(tool.toolId)?.world,
    ),
  );

  const connectedPluginTypeIds = computed(() => [
    ...new Set(pluginInstances.value.map((tool) => tool.toolId)),
  ]);

  function pluginStatus(instanceId: string) {
    const current = agent.value;
    const instance = current?.tools.find((tool) => tool.id === instanceId);
    if (!current || !instance) {
      return { status: "off" as const, reason: "Плагин не найден" };
    }
    return evaluatePluginLink(current, instance);
  }

  /** Re-enables a dormant instance of the type, otherwise creates one. */
  function connectPlugin(typeId: string): { ok: boolean; error?: string; instanceId?: string } {
    const current = agent.value;
    if (!current) return { ok: false, error: "Агент не найден" };
    const def = getToolDefinition(typeId);
    if (!def || def.world) return { ok: false, error: "Это не плагин" };
    if (!isToolImplemented(def)) return { ok: false, error: "Плагин пока без реализации в runtime" };

    const existing = current.tools.filter((tool) => tool.toolId === typeId);
    const enabled = existing.find((tool) => tool.enabled);
    if (enabled) return { ok: true, instanceId: enabled.id };

    const dormant = existing[0];
    if (dormant) {
      const tools = current.tools.map((tool) =>
        tool.id === dormant.id ? { ...tool, enabled: true } : tool,
      );
      replaceAgent(touchAgent({ ...current, tools }));
      return { ok: true, instanceId: dormant.id };
    }

    const instance = createToolInstance(typeId, {
      id: freeInstanceId(current, typeId),
      name: def.name,
      enabled: true,
      config: mergeConfigDefaults(typeId, {}),
    });
    replaceAgent(touchAgent({ ...current, tools: [...current.tools, instance] }));
    return { ok: true, instanceId: instance.id };
  }

  function disconnectPlugin(instanceId: string): { ok: boolean; error?: string } {
    const current = agent.value;
    if (!current) return { ok: false, error: "Агент не найден" };
    const tools = current.tools.map((tool) =>
      tool.id === instanceId ? { ...tool, enabled: false } : tool,
    );
    replaceAgent(touchAgent({ ...current, tools }));
    return { ok: true };
  }

  return {
    pluginTools,
    pluginInstances,
    connectedPluginTypeIds,
    pluginStatus,
    connectPlugin,
    disconnectPlugin,
  };
}
