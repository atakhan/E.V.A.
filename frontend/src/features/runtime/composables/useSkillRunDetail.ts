import { computed, onUnmounted, ref, watch, type Ref } from "vue";
import {
  cancelSkillRun,
  getRuntimeRun,
  getSkillRunHistory,
} from "@/features/runtime/services/runtimeApi";
import type { RuntimeRunResponse, SkillRunHistory } from "@/features/runtime/types/runtime";
import { TERMINAL_RUN_STATUSES } from "@/features/runtime/types/runtime";

const POLL_MS = 5000;

export function useSkillRunDetail(runId: Ref<string | undefined>) {
  const run = ref<RuntimeRunResponse | null>(null);
  const history = ref<SkillRunHistory | null>(null);
  const loading = ref(false);
  const refreshing = ref(false);
  const cancelling = ref(false);
  const error = ref<string | null>(null);

  let timer: ReturnType<typeof setInterval> | null = null;

  const isTerminal = computed(() => TERMINAL_RUN_STATUSES.has(run.value?.status ?? ""));

  async function load(loadOptions?: { silent?: boolean }) {
    const id = runId.value;
    if (!id) {
      run.value = null;
      history.value = null;
      return;
    }
    const silent = loadOptions?.silent ?? false;
    if (silent) {
      refreshing.value = true;
    } else {
      loading.value = !run.value;
    }
    if (!silent) {
      error.value = null;
    }
    try {
      const [runResponse, historyResponse] = await Promise.all([
        getRuntimeRun(id),
        getSkillRunHistory(id),
      ]);
      run.value = runResponse;
      history.value = historyResponse;
    } catch (loadError) {
      if (!silent) {
        error.value = loadError instanceof Error ? loadError.message : "Не удалось загрузить run";
      }
    } finally {
      loading.value = false;
      refreshing.value = false;
    }
  }

  async function cancel() {
    const id = runId.value;
    if (!id || isTerminal.value) return false;
    cancelling.value = true;
    error.value = null;
    try {
      await cancelSkillRun(id);
      await load();
      return true;
    } catch (cancelError) {
      error.value = cancelError instanceof Error ? cancelError.message : "Не удалось отменить run";
      return false;
    } finally {
      cancelling.value = false;
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
    if (runId.value && !isTerminal.value) {
      timer = setInterval(() => {
        void load({ silent: true });
      }, POLL_MS);
    }
  }

  watch(runId, () => {
    void load().then(schedulePolling);
  }, { immediate: true });

  watch(isTerminal, schedulePolling);
  onUnmounted(clearTimer);

  return {
    run,
    history,
    loading,
    refreshing,
    cancelling,
    error,
    isTerminal,
    reload: load,
    cancel,
  };
}
