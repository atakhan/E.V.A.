import type { Agent } from "@/features/agents/types/agent";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";
import { instancesByType } from "@/features/tools/utils/resolveToolInstance";
import { resolveRecipeTool } from "@/features/tools/utils/resolveToolInstance";

export type WorldLinkStatus = "off" | "red" | "yellow" | "green";

export interface WorldLinkEvaluation {
  status: WorldLinkStatus;
  reason: string;
  instanceId?: string;
}

function agentUsesToolInActions(agent: Agent, toolId: string): boolean {
  for (const action of agent.actions) {
    for (const step of action.recipe) {
      const resolved = resolveRecipeTool(agent, step.tool);
      if (resolved.typeId === toolId && resolved.status === "ok") return true;
      if (step.tool === toolId) return true;
    }
  }
  return false;
}

function agentListensToToolEvents(agent: Agent, toolId: string): boolean {
  const def = getToolDefinition(toolId);
  if (!def?.events.length) return false;
  const eventIds = new Set(def.events.map((event) => event.id));
  for (const skill of agent.skills) {
    for (const state of skill.states) {
      for (const transition of state.transitions) {
        const event = transition.event?.trim();
        if (event && eventIds.has(event)) return true;
      }
    }
  }
  return false;
}

function hasBehaviorPath(agent: Agent, toolId: string): boolean {
  return agentUsesToolInActions(agent, toolId) || agentListensToToolEvents(agent, toolId);
}

/**
 * Traffic-light for world kind cable (kind → agent).
 * Color is derived; not stored on the agent.
 */
export function evaluateWorldLink(agent: Agent, toolId: string): WorldLinkEvaluation {
  const def = getToolDefinition(toolId);
  if (!def?.world) {
    return { status: "off", reason: "Не мировой инструмент" };
  }

  const enabled = instancesByType(agent, toolId, true);
  if (enabled.length === 0) {
    const disabled = instancesByType(agent, toolId, false);
    if (disabled.length > 0) {
      return {
        status: "off",
        reason: "Канал отключён",
        instanceId: disabled[0]!.id,
      };
    }
    return { status: "off", reason: "Канал не подключён" };
  }

  const instance = enabled[0]!;

  if (toolId === "web_client") {
    const hasApp = (agent.world?.addresses ?? []).some(
      (address) => address.toolId === toolId && Boolean(address.credentialId?.trim()),
    );
    if (!hasApp) {
      return {
        status: "yellow",
        reason: "Нет подключённого приложения",
        instanceId: instance.id,
      };
    }
  } else if (def.credentialKind) {
    const hasCredential = Boolean(instance.credentialId?.trim());
    const addressCred = (agent.world?.addresses ?? []).some(
      (address) => address.toolId === toolId && address.credentialId?.trim(),
    );
    if (!hasCredential && !addressCred) {
      return {
        status: "red",
        reason: "Нет credential для канала",
        instanceId: instance.id,
      };
    }
  }

  if (!hasBehaviorPath(agent, toolId)) {
    return {
      status: "yellow",
      reason: "Инструмент есть, но нет действия или навыка под этот канал",
      instanceId: instance.id,
    };
  }

  return {
    status: "green",
    reason: "Канал готов",
    instanceId: instance.id,
  };
}

export function listWorldToolIdsFromCatalog(
  catalog: Array<{ id: string; world?: boolean }>,
): string[] {
  return catalog.filter((tool) => tool.world).map((tool) => tool.id);
}
