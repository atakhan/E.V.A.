import type {
  AgentInput,
  AgentMutationResult,
} from "@/features/agents/types/agent";
import { computed } from "vue";
import {
  agents,
  apiAvailable,
  archiveAgentInStorage,
  createAgentWithStorage,
  fetchArchivedAgentSummaries,
  getAgentById,
  getAgentBySlug,
  isSlugAvailable,
  removeAgentFromStorage,
  replaceAgent,
  setupTelegramOnAgent,
  touchAgent,
  unarchiveAgentInStorage,
} from "@/features/agents/services/agentsStorage";
import {
  normalizeAgentSlug,
  suggestUniqueAgentSlug,
  validateAgentSlug,
} from "@/shared/utils/agentSlug";

export function useAgents() {
  async function createAgent(input: AgentInput): Promise<AgentMutationResult> {
    const name = input.name.trim();
    if (!name) {
      return { ok: false, error: "Укажите название агента" };
    }

    const slugError = validateAgentSlug(input.slug, (candidate) => isSlugAvailable(candidate));
    if (slugError) {
      return { ok: false, error: slugError };
    }

    if (input.telegram) {
      if (!input.telegram.botToken.trim()) {
        return { ok: false, error: "Укажите bot token или отключите Telegram" };
      }
      if (!apiAvailable.value) {
        return {
          ok: false,
          error: "Для подключения Telegram нужен backend (docker compose up)",
        };
      }
    }

    try {
      const agent = await createAgentWithStorage({
        name,
        slug: input.slug,
        description: input.description,
        telegram: input.telegram,
      });
      return { ok: true, agent };
    } catch (error) {
      return {
        ok: false,
        error: error instanceof Error ? error.message : "Не удалось создать агента",
      };
    }
  }

  function updateAgent(id: string, patch: Partial<AgentInput>): AgentMutationResult {
    const agent = getAgentById(id);
    if (!agent) {
      return { ok: false, error: "Агент не найден" };
    }

    const name = patch.name?.trim() || agent.name;
    const slugCandidate = patch.slug !== undefined ? patch.slug : agent.slug;
    const slugError = validateAgentSlug(slugCandidate, (candidate) =>
      isSlugAvailable(candidate, id),
    );

    if (slugError) {
      return { ok: false, error: slugError };
    }

    const next = touchAgent({
      ...agent,
      name,
      slug: normalizeAgentSlug(slugCandidate),
      description: patch.description?.trim() ?? agent.description,
    });

    replaceAgent(next);
    return { ok: true, agent: next };
  }

  function deleteAgent(id: string) {
    const agent = getAgentById(id);
    if (!agent) return;
    void removeAgentFromStorage(agent);
  }

  async function archiveAgent(id: string): Promise<AgentMutationResult> {
    const agent = getAgentById(id);
    if (!agent) {
      return { ok: false, error: "Агент не найден" };
    }
    try {
      await archiveAgentInStorage(agent);
      return { ok: true, agent: { ...agent, archivedAt: agent.archivedAt ?? new Date().toISOString() } };
    } catch (error) {
      return {
        ok: false,
        error: error instanceof Error ? error.message : "Не удалось архивировать агента",
      };
    }
  }

  async function unarchiveAgent(id: string): Promise<AgentMutationResult> {
    const agent = getAgentById(id);
    if (!agent) {
      return { ok: false, error: "Агент не найден" };
    }
    try {
      await unarchiveAgentInStorage(agent);
      const restored = getAgentById(id);
      if (!restored) {
        return { ok: false, error: "Агент не найден после восстановления" };
      }
      return { ok: true, agent: restored };
    } catch (error) {
      return {
        ok: false,
        error: error instanceof Error ? error.message : "Не удалось восстановить агента",
      };
    }
  }

  const activeAgents = computed(() => agents.value.filter((agent) => !agent.archivedAt));

  return {
    agents,
    activeAgents,
    apiAvailable,
    getAgentById,
    getAgentBySlug,
    isSlugAvailable,
    suggestUniqueAgentSlug: (base: string, excludeAgentId?: string) =>
      suggestUniqueAgentSlug(base, (candidate) => isSlugAvailable(candidate, excludeAgentId)),
    createAgent,
    updateAgent,
    deleteAgent,
    archiveAgent,
    unarchiveAgent,
    fetchArchivedAgentSummaries,
    setupTelegramOnAgent,
  };
}
