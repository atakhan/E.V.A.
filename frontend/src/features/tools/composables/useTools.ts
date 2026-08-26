import type { ToolBinding, ToolMutationResult } from "@/features/tools/types/tool";
import { createToolBinding } from "@/features/tools/types/normalize";
import {
  builtinTools,
  getToolDefinition,
  getToolCommandIds,
} from "@/features/tools/registry/builtinTools";
import {
  getAgentBySlug,
  replaceAgent,
  touchAgent,
} from "@/features/agents/services/agentsStorage";

export function useTools() {
  function getBindings(agentSlug: string): ToolBinding[] {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return [];
    return agent.tools;
  }

  function getBinding(agentSlug: string, toolId: string): ToolBinding | undefined {
    return getBindings(agentSlug).find((binding) => binding.toolId === toolId);
  }

  function isToolEnabled(agentSlug: string, toolId: string): boolean {
    return getBinding(agentSlug, toolId)?.enabled === true;
  }

  function getEnabledToolIds(agentSlug: string): string[] {
    return getBindings(agentSlug)
      .filter((binding) => binding.enabled)
      .map((binding) => binding.toolId);
  }

  function getEnabledCommands(agentSlug: string): Array<{ toolId: string; commandId: string }> {
    return getEnabledToolIds(agentSlug).flatMap((toolId) =>
      getToolCommandIds(toolId).map((commandId) => ({ toolId, commandId })),
    );
  }

  function enableTool(agentSlug: string, toolId: string): ToolMutationResult {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return { ok: false, error: "Агент не найден" };
    if (!getToolDefinition(toolId)) return { ok: false, error: "Неизвестный Tool" };

    const existing = agent.tools.find((binding) => binding.toolId === toolId);
    let binding: ToolBinding;

    if (existing) {
      binding = { ...existing, enabled: true };
      const tools = agent.tools.map((item) =>
        item.toolId === toolId ? binding : item,
      );
      replaceAgent(touchAgent({ ...agent, tools }));
    } else {
      binding = createToolBinding(toolId);
      replaceAgent(touchAgent({ ...agent, tools: [...agent.tools, binding] }));
    }

    return { ok: true, binding };
  }

  function disableTool(agentSlug: string, toolId: string): ToolMutationResult {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return { ok: false, error: "Агент не найден" };

    const existing = agent.tools.find((binding) => binding.toolId === toolId);
    if (!existing) {
      return { ok: false, error: "Tool не подключён" };
    }

    const binding = { ...existing, enabled: false };
    const tools = agent.tools.map((item) =>
      item.toolId === toolId ? binding : item,
    );
    replaceAgent(touchAgent({ ...agent, tools }));
    return { ok: true, binding };
  }

  function setToolEnabled(agentSlug: string, toolId: string, enabled: boolean) {
    return enabled ? enableTool(agentSlug, toolId) : disableTool(agentSlug, toolId);
  }

  function updateConfigNote(agentSlug: string, toolId: string, configNote: string) {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return;

    const existing = agent.tools.find((binding) => binding.toolId === toolId);
    if (!existing) {
      const binding = createToolBinding(toolId, { enabled: false, configNote });
      replaceAgent(touchAgent({ ...agent, tools: [...agent.tools, binding] }));
      return;
    }

    const tools = agent.tools.map((item) =>
      item.toolId === toolId ? { ...item, configNote } : item,
    );
    replaceAgent(touchAgent({ ...agent, tools }));
  }

  function updateCredentialId(agentSlug: string, toolId: string, credentialId: string | undefined) {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return;

    const existing = agent.tools.find((binding) => binding.toolId === toolId);
    if (!existing) {
      const binding = createToolBinding(toolId, { enabled: false, credentialId });
      replaceAgent(touchAgent({ ...agent, tools: [...agent.tools, binding] }));
      return;
    }

    const tools = agent.tools.map((item) =>
      item.toolId === toolId ? { ...item, credentialId } : item,
    );
    replaceAgent(touchAgent({ ...agent, tools }));
  }

  return {
    catalog: builtinTools,
    getBindings,
    getBinding,
    isToolEnabled,
    getEnabledToolIds,
    getEnabledCommands,
    enableTool,
    disableTool,
    setToolEnabled,
    updateConfigNote,
    updateCredentialId,
    getToolDefinition,
    getToolCommandIds,
  };
}
