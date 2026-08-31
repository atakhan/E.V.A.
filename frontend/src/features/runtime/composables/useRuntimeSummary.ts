import { computed, onUnmounted, ref, watch, type Ref } from "vue";
import {
  getAgentRuntimeSummary,
  getRuntimeMetrics,
  getRuntimeSummary,
} from "@/features/runtime/services/runtimeApi";
import type {
  AgentRuntimeSummary,
  RuntimeMetrics,
  RuntimeSummary,
} from "@/features/runtime/types/runtime";
import { ACTIVE_RUN_STATUSES } from "@/features/runtime/types/runtime";

const POLL_MS = 5000;

export function useRuntimeSummary(options?: {
  agentSlug?: Ref<string | undefined>;
  enabled?: Ref<boolean>;
}) {
  const summary = ref<RuntimeSummary | null>(null);
  const agentSummary = ref<AgentRuntimeSummary | null>(null);
  const metrics = ref<RuntimeMetrics | null>(null);
  const loading = ref(false);
  const refreshing = ref(false);
  const error = ref<string | null>(null);

  let timer: ReturnType<typeof setInterval> | null = null;

  const hasActiveRuns = computed(() => {
    if (agentSummary.value) {
      return agentSummary.value.running + agentSummary.value.waiting > 0;
    }
    const totals = summary.value?.totals;
    if (!totals) return false;
    return totals.running + totals.waiting > 0;
  });

  const hasData = computed(() => summary.value !== null || agentSummary.value !== null);

  async function load(loadOptions?: { silent?: boolean }) {
    if (options?.enabled?.value === false) return;
    const silent = loadOptions?.silent ?? false;
    if (silent) {
      refreshing.value = true;
    } else {
      loading.value = !hasData.value;
    }
    if (!silent) {
      error.value = null;
    }
    try {
      const slug = options?.agentSlug?.value;
      if (slug) {
        agentSummary.value = await getAgentRuntimeSummary(slug);
        summary.value = null;
      } else {
        summary.value = await getRuntimeSummary();
        agentSummary.value = null;
      }
      metrics.value = await getRuntimeMetrics();
    } catch (loadError) {
      if (!silent) {
        error.value = loadError instanceof Error ? loadError.message : "Не удалось загрузить summary";
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
    () => [options?.agentSlug?.value, options?.enabled?.value],
    () => {
      void load().then(schedulePolling);
    },
    { immediate: true },
  );

  watch(hasActiveRuns, schedulePolling);

  onUnmounted(clearTimer);

  return {
    summary,
    agentSummary,
    metrics,
    loading,
    refreshing,
    error,
    hasActiveRuns,
    reload: load,
  };
}

export function isActiveRunStatus(status: string): boolean {
  return ACTIVE_RUN_STATUSES.has(status);
}
