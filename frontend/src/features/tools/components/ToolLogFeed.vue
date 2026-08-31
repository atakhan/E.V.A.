<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  fetchAgentToolLogs,
  type ToolApiLog,
} from "@/features/tools/services/toolLogsApi";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";
import {
  formatLogTime,
  logPreview,
  logStatusCode,
  logUsageLabel,
  shortCredentialId,
  shortSkillRunId,
} from "@/features/tools/utils/toolLogFormat";
import { agentLogsPath } from "@/router/paths";

const props = withDefaults(
  defineProps<{
    agentSlug: string;
    toolId?: string;
    credentialId?: string;
    skillRunId?: string;
    command?: string;
    status?: string;
    limit?: number;
    compact?: boolean;
    showHeader?: boolean;
    showLinkToAll?: boolean;
    showAutoRefreshToggle?: boolean;
    autoRefreshMs?: number;
    autoRefreshDefault?: boolean;
    emptyText?: string;
  }>(),
  {
    limit: 30,
    compact: false,
    showHeader: true,
    showLinkToAll: false,
    showAutoRefreshToggle: false,
    autoRefreshMs: 0,
    autoRefreshDefault: false,
    emptyText: "Пока нет записей",
  },
);

const router = useRouter();
const logs = ref<ToolApiLog[]>([]);
const total = ref(0);
const loading = ref(false);
const expandedId = ref<string | null>(null);
const autoRefreshOn = ref(props.autoRefreshDefault);
let refreshTimer: ReturnType<typeof setInterval> | null = null;

const title = computed(() => {
  if (props.toolId) {
    return getToolDefinition(props.toolId)?.name ?? props.toolId;
  }
  return "Все Tools";
});

const effectiveRefreshMs = computed(() =>
  autoRefreshOn.value && props.autoRefreshMs > 0 ? props.autoRefreshMs : 0,
);

function toolLabel(toolId: string): string {
  return getToolDefinition(toolId)?.name ?? toolId;
}

function toggleExpand(id: string) {
  expandedId.value = expandedId.value === id ? null : id;
}

function clearRefreshTimer() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

function setupRefreshTimer() {
  clearRefreshTimer();
  const ms = effectiveRefreshMs.value;
  if (ms > 0) {
    refreshTimer = setInterval(() => void load(true), ms);
  }
}

async function load(silent = false) {
  if (!silent || !logs.value.length) {
    loading.value = true;
  }
  try {
    const page = await fetchAgentToolLogs(props.agentSlug, {
      toolId: props.toolId,
      credentialId: props.credentialId,
      skillRunId: props.skillRunId,
      command: props.command,
      status: props.status,
      limit: props.limit,
      offset: 0,
    });
    logs.value = page.items;
    total.value = page.total;
  } catch {
    if (!silent) {
      logs.value = [];
      total.value = 0;
    }
  } finally {
    loading.value = false;
  }
}

function openAllLogs() {
  void router.push(
    agentLogsPath(props.agentSlug, {
      tool: props.toolId,
      skillRunId: props.skillRunId,
    }),
  );
}

function toggleAutoRefresh() {
  autoRefreshOn.value = !autoRefreshOn.value;
  setupRefreshTimer();
}

watch(
  () =>
    [
      props.agentSlug,
      props.toolId,
      props.credentialId,
      props.skillRunId,
      props.command,
      props.status,
      props.limit,
    ] as const,
  () => void load(),
  { immediate: true },
);

watch(effectiveRefreshMs, () => setupRefreshTimer());

onMounted(() => setupRefreshTimer());

onUnmounted(() => clearRefreshTimer());

defineExpose({ reload: load });
</script>

<template>
  <section>
    <div v-if="showHeader" class="mb-1.5 flex items-center justify-between gap-2">
      <h5 class="text-xs font-semibold">
        {{ compact ? "Последние вызовы" : title }}
      </h5>
      <div class="flex items-center gap-2 text-[11px] text-base-content/50">
        <span>{{ total }} всего</span>
        <label
          v-if="showAutoRefreshToggle && autoRefreshMs > 0"
          class="flex cursor-pointer items-center gap-1"
        >
          <input
            type="checkbox"
            class="checkbox checkbox-xs"
            :checked="autoRefreshOn"
            @change="toggleAutoRefresh"
          />
          авто
        </label>
        <span
          v-else-if="effectiveRefreshMs > 0"
          class="badge badge-ghost badge-xs"
          title="Автообновление"
        >
          ↻ {{ Math.round(effectiveRefreshMs / 1000) }}s
        </span>
        <button type="button" class="btn btn-ghost btn-xs" :disabled="loading" @click="load()">
          ↻
        </button>
        <button
          v-if="showLinkToAll"
          type="button"
          class="btn btn-ghost btn-xs"
          @click="openAllLogs"
        >
          Все логи →
        </button>
      </div>
    </div>

    <div
      v-if="loading && !logs.length"
      class="rounded-lg border border-dashed border-base-300 px-3 py-4 text-center text-xs text-base-content/50"
    >
      Загрузка…
    </div>
    <div
      v-else-if="!logs.length"
      class="rounded-lg border border-dashed border-base-300 px-3 py-4 text-center text-xs text-base-content/50"
    >
      {{ emptyText }}
    </div>
    <ul v-else class="space-y-1" :class="compact ? 'max-h-52 overflow-y-auto' : ''">
      <li
        v-for="log in logs"
        :key="log.id"
        class="rounded-lg border border-base-300 bg-base-100"
      >
        <button
          type="button"
          class="flex w-full flex-col gap-1 px-3 py-2 text-left text-xs hover:bg-base-200/30"
          @click="toggleExpand(log.id)"
        >
          <div class="flex flex-wrap items-center gap-x-2 gap-y-0.5">
            <span class="text-base-content/50">{{ formatLogTime(log.createdAt) }}</span>
            <span
              v-if="!toolId"
              class="badge badge-ghost badge-xs font-mono"
            >
              {{ toolLabel(log.toolId) }}
            </span>
            <span class="font-mono">{{ log.command }}</span>
            <span
              class="badge badge-xs"
              :class="log.status === 'ok' ? 'badge-success' : 'badge-error'"
            >
              {{ log.status }}
            </span>
            <span v-if="log.durationMs != null" class="text-base-content/50">
              {{ log.durationMs }} ms
            </span>
            <span v-if="log.model" class="truncate font-mono text-base-content/55">
              {{ log.model }}
            </span>
            <span v-if="logUsageLabel(log)" class="text-base-content/50">
              {{ logUsageLabel(log) }}
            </span>
            <span v-if="logStatusCode(log)" class="text-base-content/50">
              HTTP {{ logStatusCode(log) }}
            </span>
          </div>
          <p class="line-clamp-2 font-mono text-[11px] text-base-content/70">
            {{ logPreview(log) }}
          </p>
          <p v-if="log.errorMessage" class="text-error">{{ log.errorMessage }}</p>
          <div
            v-if="!compact && (log.actionId || log.skillRunId || log.credentialId)"
            class="flex flex-wrap gap-2 text-[10px] text-base-content/45"
          >
            <span v-if="log.actionId">action: {{ log.actionId }}</span>
            <span v-if="log.skillRunId">run: {{ shortSkillRunId(log.skillRunId) }}</span>
            <span v-if="log.credentialId">cred: {{ shortCredentialId(log.credentialId) }}</span>
          </div>
        </button>

        <div
          v-if="expandedId === log.id"
          class="grid gap-2 border-t border-base-300/60 bg-base-200/20 px-3 py-2 text-[11px]"
        >
          <div class="grid gap-2 md:grid-cols-2">
            <div>
              <p class="mb-1 font-medium">Request</p>
              <pre class="max-h-40 overflow-auto rounded border border-base-300 bg-base-100 p-2 font-mono">{{ JSON.stringify(log.requestSummary, null, 2) }}</pre>
            </div>
            <div>
              <p class="mb-1 font-medium">Response</p>
              <pre class="max-h-40 overflow-auto rounded border border-base-300 bg-base-100 p-2 font-mono">{{ JSON.stringify(log.responseSummary, null, 2) }}</pre>
            </div>
          </div>
          <div v-if="Object.keys(log.usage).length">
            <p class="mb-1 font-medium">Usage</p>
            <pre class="rounded border border-base-300 bg-base-100 p-2 font-mono">{{ JSON.stringify(log.usage, null, 2) }}</pre>
          </div>
        </div>
      </li>
    </ul>
  </section>
</template>
