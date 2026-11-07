import { computed, onUnmounted, ref, watch, type Ref } from "vue";
import { apiAvailable, storageReady } from "@/features/agents/services/agentsStorage";
import { getAgentMemory } from "@/features/runtime/services/runtimeApi";
import type { AgentMemory, AgentMemoryRun } from "@/features/runtime/types/runtime";
import { ACTIVE_RUN_STATUSES } from "@/features/runtime/types/runtime";

const POLL_MS = 5000;

function hasLiveRun(runs: AgentMemoryRun[]): boolean {
  return runs.some((run) => ACTIVE_RUN_STATUSES.has(run.status));
}

export function useAgentMemory(agentSlug: Ref<string>) {
  const memory = ref<AgentMemory | null>(null);
  const loading = ref(false);
  const refreshing = ref(false);
  const error = ref<string | null>(null);

  let timer: ReturnType<typeof setInterval> | null = null;

  const live = computed(() => (memory.value ? hasLiveRun(memory.value.runs) : false));

  async function load(options?: { silent?: boolean }) {
    if (!agentSlug.value) return;
    const silent = options?.silent ?? false;
    if (!apiAvailable.value) {
      if (!silent) {
        loading.value = !storageReady.value;
        error.value = storageReady.value ? "Runtime не отвечает" : null;
      }
      refreshing.value = false;
      return;
    }
    if (silent) {
      refreshing.value = true;
    } else {
      loading.value = memory.value === null;
      error.value = null;
    }
    try {
      memory.value = await getAgentMemory(agentSlug.value);
    } catch (loadError) {
      if (!silent) {
        error.value = loadError instanceof Error ? loadError.message : "Не удалось прочитать память";
      }
    } finally {
      loading.value = false;
      refreshing.value = false;
    }
  }

  function clearTimer() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  function schedulePolling() {
    clearTimer();
    if (live.value) {
      timer = setInterval(() => {
        void load({ silent: true });
      }, POLL_MS);
    }
  }

  watch(
    () => [agentSlug.value, apiAvailable.value, storageReady.value] as const,
    ([slug], previous) => {
      if (!previous || previous[0] !== slug) memory.value = null;
      void load().then(schedulePolling);
    },
    { immediate: true },
  );

  watch(live, schedulePolling);

  onUnmounted(clearTimer);

  return { memory, loading, refreshing, error, reload: load };
}

