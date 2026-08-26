import { computed, ref } from "vue";
import type { Agent } from "@/features/agents/types/agent";
import { saveAgentApi, publishAgentApi } from "@/features/agents/services/agentsApi";
import { apiAvailable } from "@/features/agents/services/agentsStorage";
import {
  createRuntimeRun,
  listPublicationsApi,
  postRuntimeEvent,
} from "@/features/runtime/services/runtimeApi";
import type { AgentPublicationSummary, RuntimeRunResponse } from "@/features/runtime/types/runtime";
import {
  createSimConversationId,
  getSkillEntryEvents,
  getSkillFollowUpEvents,
} from "@/features/runtime/utils/skillEvents";

export function useAgentRuntime(agent: () => Agent | undefined) {
  const publications = ref<AgentPublicationSummary[]>([]);
  const loadingPublications = ref(false);
  const publishing = ref(false);
  const running = ref(false);
  const error = ref<string | null>(null);

  const activeRun = ref<RuntimeRunResponse | null>(null);
  const selectedSkillId = ref("");
  const eventType = ref("");
  const conversationId = ref("");
  const messageText = ref("");

  const latestPublication = computed(() => publications.value[0] ?? null);
  const isPublished = computed(() => publications.value.length > 0);

  const currentAgent = computed(() => agent());

  const selectedSkill = computed(() =>
    currentAgent.value?.skills.find((skill) => skill.id === selectedSkillId.value),
  );

  const entryEvents = computed(() =>
    selectedSkill.value ? getSkillEntryEvents(selectedSkill.value) : [],
  );

  const followUpEvents = computed(() => {
    if (!selectedSkill.value || !activeRun.value) {
      return [];
    }
    return getSkillFollowUpEvents(selectedSkill.value, activeRun.value.currentState);
  });

  const canContinueRun = computed(
    () => activeRun.value?.status === "waiting" && !!activeRun.value.skillRunId,
  );

  const isTerminalRun = computed(() =>
    ["completed", "error"].includes(activeRun.value?.status ?? ""),
  );

  async function loadPublications(slug: string) {
    if (!apiAvailable.value) {
      publications.value = [];
      return;
    }

    loadingPublications.value = true;
    error.value = null;
    try {
      publications.value = await listPublicationsApi(slug);
    } catch (loadError) {
      publications.value = [];
      error.value =
        loadError instanceof Error ? loadError.message : "Не удалось загрузить публикации";
    } finally {
      loadingPublications.value = false;
    }
  }

  function resetRunForm(slug: string) {
    const skills = currentAgent.value?.skills ?? [];
    selectedSkillId.value = skills[0]?.id ?? "";
    eventType.value = skills[0] ? getSkillEntryEvents(skills[0])[0] ?? "channel.message.received" : "";
    conversationId.value = createSimConversationId(slug);
    messageText.value = "";
    activeRun.value = null;
    error.value = null;
  }

  function syncSkillSelection() {
    const skills = currentAgent.value?.skills ?? [];
    if (!skills.length) {
      selectedSkillId.value = "";
      eventType.value = "";
      return;
    }

    if (!skills.some((skill) => skill.id === selectedSkillId.value)) {
      selectedSkillId.value = skills[0].id;
    }

    const events = entryEvents.value;
    if (!events.includes(eventType.value)) {
      eventType.value = events[0] ?? "channel.message.received";
    }
  }

  async function publishDraft(slug: string) {
    const draft = currentAgent.value;
    if (!draft) {
      return { ok: false as const, error: "Агент не найден" };
    }
    if (!apiAvailable.value) {
      return { ok: false as const, error: "Backend недоступен" };
    }

    publishing.value = true;
    error.value = null;
    try {
      await saveAgentApi(draft);
      const result = await publishAgentApi(slug);
      await loadPublications(slug);
      return { ok: true as const, version: result.version };
    } catch (publishError) {
      const message =
        publishError instanceof Error ? publishError.message : "Не удалось опубликовать агента";
      error.value = message;
      return { ok: false as const, error: message };
    } finally {
      publishing.value = false;
    }
  }

  async function sendEvent(slug: string) {
    if (!selectedSkillId.value) {
      error.value = "Выберите skill";
      return;
    }

    const text = messageText.value.trim();
    if (!text) {
      error.value = "Введите текст сообщения";
      return;
    }

    const payload: Record<string, unknown> = {
      conversation_id: conversationId.value,
      text,
    };

    running.value = true;
    error.value = null;

    try {
      const type =
        canContinueRun.value && followUpEvents.value.length
          ? followUpEvents.value.includes(eventType.value)
            ? eventType.value
            : followUpEvents.value[0]
          : eventType.value;

      const response = canContinueRun.value && activeRun.value
        ? await postRuntimeEvent({
            skillRunId: activeRun.value.skillRunId,
            eventType: type,
            payload,
          })
        : await createRuntimeRun({
            agentSlug: slug,
            skillId: selectedSkillId.value,
            eventType: type,
            payload,
          });

      activeRun.value = response;
    } catch (runError) {
      error.value = runError instanceof Error ? runError.message : "Ошибка runtime";
    } finally {
      running.value = false;
    }
  }

  function newConversation(slug: string) {
    conversationId.value = createSimConversationId(slug);
    activeRun.value = null;
    error.value = null;
  }

  return {
    publications,
    latestPublication,
    isPublished,
    loadingPublications,
    publishing,
    running,
    error,
    activeRun,
    selectedSkillId,
    eventType,
    conversationId,
    messageText,
    entryEvents,
    followUpEvents,
    canContinueRun,
    isTerminalRun,
    loadPublications,
    resetRunForm,
    syncSkillSelection,
    publishDraft,
    sendEvent,
    newConversation,
  };
}
