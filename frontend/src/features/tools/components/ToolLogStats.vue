<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import {
  fetchAgentToolLogStats,
  type ToolLogStats,
} from "@/features/tools/services/toolLogsApi";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";

const props = defineProps<{
  agentSlug: string;
  toolId?: string;
  credentialId?: string;
  skillRunId?: string;
  hours?: number;
}>();

const stats = ref<ToolLogStats | null>(null);
const loading = ref(false);

const successRate = computed(() => {
  if (!stats.value || stats.value.total === 0) return null;
  return Math.round((stats.value.ok / stats.value.total) * 100);
});

function toolLabel(toolId: string): string {
  return getToolDefinition(toolId)?.name ?? toolId;
}

async function load() {
  loading.value = true;
  try {
    stats.value = await fetchAgentToolLogStats(props.agentSlug, {
      toolId: props.toolId,
      credentialId: props.credentialId,
      skillRunId: props.skillRunId,
      hours: props.hours,
    });
  } catch {
    stats.value = null;
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.agentSlug, props.toolId, props.credentialId, props.skillRunId, props.hours] as const,
  () => void load(),
);

onMounted(() => void load());

defineExpose({ reload: load });
</script>

<template>
  <div v-if="loading && !stats" class="text-xs text-base-content/50">Загрузка аналитики…</div>
  <div v-else-if="stats" class="space-y-3">
    <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
      <div class="rounded-lg border border-base-300 bg-base-100 px-3 py-2">
        <p class="text-[10px] uppercase tracking-wide text-base-content/50">Всего</p>
        <p class="text-lg font-semibold">{{ stats.total }}</p>
      </div>
      <div class="rounded-lg border border-base-300 bg-base-100 px-3 py-2">
        <p class="text-[10px] uppercase tracking-wide text-base-content/50">Успех</p>
        <p class="text-lg font-semibold text-success">
          {{ stats.ok }}
          <span v-if="successRate != null" class="text-xs font-normal text-base-content/50">
            ({{ successRate }}%)
          </span>
        </p>
      </div>
      <div class="rounded-lg border border-base-300 bg-base-100 px-3 py-2">
        <p class="text-[10px] uppercase tracking-wide text-base-content/50">Ошибки</p>
        <p class="text-lg font-semibold" :class="stats.error ? 'text-error' : ''">{{ stats.error }}</p>
      </div>
      <div class="rounded-lg border border-base-300 bg-base-100 px-3 py-2">
        <p class="text-[10px] uppercase tracking-wide text-base-content/50">Ср. время</p>
        <p class="text-lg font-semibold">
          {{ stats.avgDurationMs != null ? `${stats.avgDurationMs} ms` : "—" }}
        </p>
      </div>
    </div>

    <div v-if="Object.keys(stats.usageTotals).length" class="flex flex-wrap gap-2 text-xs">
      <span
        v-for="(value, key) in stats.usageTotals"
        :key="key"
        class="badge badge-ghost badge-sm font-mono"
      >
        {{ key }}: {{ value }}
      </span>
    </div>

    <div v-if="stats.byTool.length" class="grid gap-3 md:grid-cols-2">
      <div class="rounded-lg border border-base-300 bg-base-100 p-3">
        <p class="mb-2 text-xs font-medium">По Tools</p>
        <ul class="space-y-1 text-xs">
          <li
            v-for="row in stats.byTool"
            :key="row.toolId"
            class="flex items-center justify-between gap-2"
          >
            <span class="font-mono">{{ toolLabel(row.toolId) }}</span>
            <span class="text-base-content/60">
              {{ row.count }}
              <template v-if="row.errors"> · {{ row.errors }} err</template>
              <template v-if="row.avgDurationMs != null"> · {{ row.avgDurationMs }} ms</template>
            </span>
          </li>
        </ul>
      </div>
      <div class="rounded-lg border border-base-300 bg-base-100 p-3">
        <p class="mb-2 text-xs font-medium">Топ commands</p>
        <ul class="space-y-1 text-xs font-mono">
          <li
            v-for="row in stats.byCommand"
            :key="`${row.toolId}:${row.command}`"
            class="flex items-center justify-between gap-2"
          >
            <span class="truncate">{{ row.toolId }}.{{ row.command }}</span>
            <span class="shrink-0 text-base-content/60">{{ row.count }}</span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
