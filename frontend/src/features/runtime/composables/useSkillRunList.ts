import { computed, onUnmounted, ref, watch, type Ref } from "vue";
import { listSkillRuns } from "@/features/runtime/services/runtimeApi";
import type { SkillRunStatusFilter, SkillRunSummary } from "@/features/runtime/types/runtime";
import { isActiveRunStatus } from "@/features/runtime/composables/useRuntimeSummary";

const POLL_MS = 5000;

export function useSkillRunList(options: {
  agentSlug?: Ref<string | undefined>;
  statusFilter: Ref<SkillRunStatusFilter>;
  skillId?: Ref<string | undefined>;
  activeOnly?: Ref<boolean>;
  limit?: number;
}) {
  const items = ref<SkillRunSummary[]>([]);
  const total = ref(0);
  const loading = ref(false);
  const refreshing = ref(false);
  const error = ref<string | null>(null);

  let timer: ReturnType<typeof setInterval> | null = null;

  const hasActiveRuns = computed(() => items.value.some((item) => isActiveRunStatus(item.status)));

  async function load(loadOptions?: { silent?: boolean }) {
    const silent = loadOptions?.silent ?? false;
    if (silent) {
      refreshing.value = true;
    } else {
      loading.value = items.value.length === 0;
    }
    if (!silent) {
      error.value = null;
    }
    try {
      const response = await listSkillRuns({
        agentSlug: options.agentSlug?.value,
        skillId: options.skillId?.value || undefined,
        statusFilter: options.statusFilter.value === "all" ? undefined : options.statusFilter.value,
        activeOnly: options.activeOnly?.value,
        limit: options.limit ?? 50,
      });
      items.value = response.items;
      total.value = response.total;
    } catch (loadError) {
      if (!silent) {
        error.value = loadError instanceof Error ? loadError.message : "Не удалось загрузить runs";
        items.value = [];
        total.value = 0;
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
    if (hasActiveRuns.value) {
      timer = setInterval(() => {
        void load({ silent: true });
      }, POLL_MS);
    }
  }

  watch(
    () => [
      options.agentSlug?.value,
      options.statusFilter.value,
      options.skillId?.value,
      options.activeOnly?.value,
    ],
    () => {
      void load().then(schedulePolling);
    },
    { immediate: true },
  );

  watch(hasActiveRuns, schedulePolling);
  onUnmounted(clearTimer);

  return {
    items,
    total,
    loading,
    refreshing,
    error,
    hasActiveRuns,
    reload: load,
  };
}
