import type { ToolInstance, ToolMutationResult } from "@/features/tools/types/tool";
import { createToolInstance } from "@/features/tools/types/normalize";
import {
  getBuiltinTools,
  getToolCommandIds,
  getToolDefinition,
} from "@/features/tools/registry/builtinTools";
import {
  getAgentBySlug,
  replaceAgent,
  touchAgent,
} from "@/features/agents/services/agentsStorage";

export function useTools() {
  function getInstances(agentSlug: string): ToolInstance[] {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return [];
    return agent.tools;
  }

  function getInstance(agentSlug: string, instanceId: string): ToolInstance | undefined {
    return getInstances(agentSlug).find((item) => item.id === instanceId);
  }

  function getInstancesByType(agentSlug: string, typeId: string): ToolInstance[] {
    return getInstances(agentSlug).filter((item) => item.toolId === typeId);
  }

  /** @deprecated use getInstance */
  function getBinding(agentSlug: string, toolId: string): ToolInstance | undefined {
    return getInstances(agentSlug).find((item) => item.toolId === toolId);
  }

  function isInstanceEnabled(agentSlug: string, instanceId: string): boolean {
    return getInstance(agentSlug, instanceId)?.enabled === true;
  }

  /** @deprecated */
  function isToolEnabled(agentSlug: string, toolId: string): boolean {
    return getInstancesByType(agentSlug, toolId).some((item) => item.enabled);
  }

  function getEnabledInstances(agentSlug: string): ToolInstance[] {
    return getInstances(agentSlug).filter((item) => item.enabled);
  }

  /** @deprecated use getEnabledInstances — returns instance ids */
  function getEnabledToolIds(agentSlug: string): string[] {
    return getEnabledInstances(agentSlug).map((item) => item.id);
  }

  function getEnabledCommands(agentSlug: string): Array<{ instanceId: string; toolId: string; commandId: string }> {
    return getEnabledInstances(agentSlug).flatMap((instance) =>
      getToolCommandIds(instance.toolId).map((commandId) => ({
        instanceId: instance.id,
        toolId: instance.toolId,
        commandId,
      })),
    );
  }

  function addInstance(agentSlug: string, typeId: string, partial?: Partial<ToolInstance>): ToolMutationResult {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return { ok: false, error: "Агент не найден" };
    if (!getToolDefinition(typeId)) return { ok: false, error: "Неизвестный Tool" };

    const existing = partial?.id ? getInstance(agentSlug, partial.id) : undefined;
    if (existing) return { ok: false, error: "Instance с таким id уже есть" };

    const instance = createToolInstance(typeId, partial);
    replaceAgent(touchAgent({ ...agent, tools: [...agent.tools, instance] }));
    return { ok: true, instance };
  }

  function updateInstance(
    agentSlug: string,
    instanceId: string,
    patch: Partial<ToolInstance>,
  ): ToolMutationResult {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return { ok: false, error: "Агент не найден" };
    const existing = getInstance(agentSlug, instanceId);
    if (!existing) return { ok: false, error: "Instance не найден" };

    const instance: ToolInstance = {
      ...existing,
      ...patch,
      id: existing.id,
      toolId: existing.toolId,
      config: patch.config ?? existing.config,
    };
    const tools = agent.tools.map((item) => (item.id === instanceId ? instance : item));
    replaceAgent(touchAgent({ ...agent, tools }));
    return { ok: true, instance };
  }

  function removeInstance(agentSlug: string, instanceId: string): ToolMutationResult {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return { ok: false, error: "Агент не найден" };
    const existing = getInstance(agentSlug, instanceId);
    if (!existing) return { ok: false, error: "Instance не найден" };
    replaceAgent(touchAgent({ ...agent, tools: agent.tools.filter((item) => item.id !== instanceId) }));
    return { ok: true, instance: existing };
  }

  function setInstanceEnabled(agentSlug: string, instanceId: string, enabled: boolean): ToolMutationResult {
    return updateInstance(agentSlug, instanceId, { enabled });
  }

  /** @deprecated use addInstance */
  function enableTool(agentSlug: string, toolId: string): ToolMutationResult {
    const existing = getBinding(agentSlug, toolId);
    if (existing) return setInstanceEnabled(agentSlug, existing.id, true);
    return addInstance(agentSlug, toolId, { id: toolId });
  }

  /** @deprecated */
  function disableTool(agentSlug: string, toolId: string): ToolMutationResult {
    const existing = getBinding(agentSlug, toolId);
    if (!existing) return { ok: false, error: "Tool не подключён" };
    return setInstanceEnabled(agentSlug, existing.id, false);
  }

  function setToolEnabled(agentSlug: string, toolId: string, enabled: boolean) {
    return enabled ? enableTool(agentSlug, toolId) : disableTool(agentSlug, toolId);
  }

  function updateConfig(agentSlug: string, instanceId: string, config: Record<string, unknown>) {
    return updateInstance(agentSlug, instanceId, { config });
  }

  /** @deprecated */
  function updateConfigNote(agentSlug: string, toolId: string, configNote: string) {
    const existing = getBinding(agentSlug, toolId);
    if (!existing) {
      return addInstance(agentSlug, toolId, { enabled: false, configNote });
    }
    try {
      const config = configNote.trim().startsWith("{") ? JSON.parse(configNote) : { note: configNote };
      return updateInstance(agentSlug, existing.id, { config });
    } catch {
      return updateInstance(agentSlug, existing.id, { config: { note: configNote } });
    }
  }

  function updateCredentialId(agentSlug: string, instanceId: string, credentialId: string | undefined) {
    return updateInstance(agentSlug, instanceId, { credentialId });
  }

  return {
    catalog: getBuiltinTools(),
    getInstances,
    getInstance,
    getInstancesByType,
    getBindings: getInstances,
    getBinding,
    isInstanceEnabled,
    isToolEnabled,
    getEnabledInstances,
    getEnabledToolIds,
    getEnabledCommands,
    addInstance,
    updateInstance,
    removeInstance,
    setInstanceEnabled,
    enableTool,
    disableTool,
    setToolEnabled,
    updateConfig,
    updateConfigNote,
    updateCredentialId,
    getToolDefinition,
    getToolCommandIds,
  };
}
