import { computed } from "vue";
import {
  getAgentBySlug,
  replaceAgent,
  touchAgent,
} from "@/features/agents/services/agentsStorage";
import type { WorldAddress } from "@/features/agents/types/world";
import { createEmptyAgentWorld } from "@/features/agents/types/world";
import { evaluateWorldLink } from "@/features/agents/utils/evaluateWorldLink";
import { createToolInstance } from "@/features/tools/types/normalize";
import { getBuiltinTools, getToolDefinition } from "@/features/tools/registry/builtinTools";
import { createId } from "@/shared/utils/id";

export function useWorldConnections(agentSlug: () => string) {
  const agent = computed(() => getAgentBySlug(agentSlug()));

  const worldTools = computed(() => getBuiltinTools().filter((tool) => tool.world));

  const connectedToolIds = computed(() => {
    const current = agent.value;
    if (!current) return [] as string[];
    const ids = new Set<string>();
    for (const tool of current.tools) {
      if (!tool.enabled) continue;
      if (getToolDefinition(tool.toolId)?.world) ids.add(tool.toolId);
    }
    return [...ids];
  });

  const unconnectedWorldTools = computed(() =>
    worldTools.value.filter((tool) => !connectedToolIds.value.includes(tool.id)),
  );

  function linkStatus(toolId: string) {
    const current = agent.value;
    if (!current) {
      return { status: "off" as const, reason: "Агент не найден" };
    }
    return evaluateWorldLink(current, toolId);
  }

  function connectKind(toolId: string): { ok: boolean; error?: string } {
    const current = agent.value;
    if (!current) return { ok: false, error: "Агент не найден" };
    const def = getToolDefinition(toolId);
    if (!def?.world) return { ok: false, error: "Не мировой инструмент" };

    const existing = current.tools.filter((tool) => tool.toolId === toolId);
    if (existing.some((tool) => tool.enabled)) {
      return { ok: true };
    }

    if (existing.length > 0) {
      const primary = existing[0]!;
      const tools = current.tools.map((tool) =>
        tool.id === primary.id
          ? { ...tool, enabled: true }
          : tool.toolId === toolId
            ? { ...tool, enabled: false }
            : tool,
      );
      replaceAgent(touchAgent({ ...current, tools }));
      return { ok: true };
    }

    const instance = createToolInstance(toolId, {
      name: def.name,
      enabled: true,
    });
    replaceAgent(touchAgent({ ...current, tools: [...current.tools, instance] }));
    return { ok: true };
  }

  function disconnectKind(toolId: string): { ok: boolean; error?: string } {
    const current = agent.value;
    if (!current) return { ok: false, error: "Агент не найден" };
    const tools = current.tools.map((tool) =>
      tool.toolId === toolId ? { ...tool, enabled: false } : tool,
    );
    replaceAgent(touchAgent({ ...current, tools }));
    return { ok: true };
  }

  function addAddress(toolId: string, name?: string): WorldAddress | null {
    const current = agent.value;
    if (!current) return null;
    if (!connectedToolIds.value.includes(toolId)) return null;

    const address: WorldAddress = {
      id: createId(),
      toolId,
      name: name?.trim() || `Адрес ${toolId}`,
      config: {},
    };
    const world = current.world ?? createEmptyAgentWorld();
    replaceAgent(
      touchAgent({
        ...current,
        world: { addresses: [...world.addresses, address] },
      }),
    );
    return address;
  }

  function removeAddress(addressId: string) {
    const current = agent.value;
    if (!current?.world) return;
    replaceAgent(
      touchAgent({
        ...current,
        world: {
          addresses: current.world.addresses.filter((item) => item.id !== addressId),
        },
      }),
    );
  }

  function updateAddress(
    addressId: string,
    patch: Partial<Pick<WorldAddress, "name" | "credentialId" | "config">>,
  ) {
    const current = agent.value;
    if (!current?.world) return;
    replaceAgent(
      touchAgent({
        ...current,
        world: {
          addresses: current.world.addresses.map((item) => {
            if (item.id !== addressId) return item;
            return {
              ...item,
              ...patch,
              config:
                patch.config !== undefined
                  ? patch.config
                  : (item.config ?? {}),
            };
          }),
        },
      }),
    );
  }

  function getAddress(addressId: string): WorldAddress | undefined {
    return agent.value?.world?.addresses.find((item) => item.id === addressId);
  }

  function addressesFor(toolId: string): WorldAddress[] {
    return (agent.value?.world?.addresses ?? []).filter((item) => item.toolId === toolId);
  }

  return {
    worldTools,
    connectedToolIds,
    unconnectedWorldTools,
    linkStatus,
    connectKind,
    disconnectKind,
    addAddress,
    removeAddress,
    updateAddress,
    getAddress,
    addressesFor,
  };
}
