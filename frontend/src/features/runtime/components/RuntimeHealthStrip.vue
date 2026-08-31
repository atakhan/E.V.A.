<script setup lang="ts">
import { computed } from "vue";
import type { AgentRuntimeSummary, RuntimeMetrics, RuntimeSummary } from "@/features/runtime/types/runtime";

const props = defineProps<{
  summary?: RuntimeSummary | null;
  agentSummary?: AgentRuntimeSummary | null;
  metrics?: RuntimeMetrics | null;
  loading?: boolean;
  refreshing?: boolean;
}>();

const counts = computed(() => {
  if (props.agentSummary) {
    return {
      running: props.agentSummary.running,
      waiting: props.agentSummary.waiting,
      error: props.agentSummary.error,
      publication: props.agentSummary.latestPublicationVersion,
      isPublished: props.agentSummary.isPublished,
    };
  }
  const totals = props.summary?.totals;
  return {
    running: totals?.running ?? 0,
    waiting: totals?.waiting ?? 0,
    error: totals?.error ?? 0,
    publication: null,
    isPublished: false,
  };
});
</script>

<template>
  <div class="relative rounded-2xl border border-base-300 bg-base-100 p-4 shadow-sm">
    <span
      v-if="refreshing"
      class="absolute right-3 top-3 loading loading-spinner loading-xs text-base-content/40"
      aria-label="Обновление"
    />
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wide text-base-content/50">Runtime health</p>
        <p v-if="loading && !summary && !agentSummary" class="mt-1 text-sm text-base-content/60">
          Загрузка…
        </p>
        <p v-else class="mt-1 text-sm text-base-content/70">
          <span v-if="agentSummary">
            Публикация:
            <span class="font-mono">
              {{ counts.isPublished ? `v${counts.publication}` : "не опубликован" }}
            </span>
          </span>
          <span v-else>Глобальный срез runtime</span>
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <span class="badge badge-info badge-outline">running {{ counts.running }}</span>
        <span class="badge badge-warning badge-outline">waiting {{ counts.waiting }}</span>
        <span class="badge badge-error badge-outline">error {{ counts.error }}</span>
        <span
          v-if="summary?.totals.completed24h !== undefined"
          class="badge badge-ghost badge-outline"
        >
          completed 24h {{ summary.totals.completed24h }}
        </span>
      </div>
    </div>
    <p v-if="metrics" class="mt-3 text-xs text-base-content/45">
      worker metrics: events {{ metrics.events_processed }} · active {{ metrics.runs_active }} ·
      action failures {{ metrics.action_failures }}
    </p>
  </div>
</template>
