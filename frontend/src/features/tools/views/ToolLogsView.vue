<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import ToolLogFeed from "@/features/tools/components/ToolLogFeed.vue";
import ToolLogStats from "@/features/tools/components/ToolLogStats.vue";
import {
  fetchAllAgentToolLogs,
} from "@/features/tools/services/toolLogsApi";
import { builtinTools } from "@/features/tools/registry/builtinTools";
import {
  downloadToolLogsCsv,
  downloadToolLogsJson,
} from "@/features/tools/utils/toolLogExport";

const props = defineProps<{
  agentSlug: string;
}>();

const route = useRoute();

const toolFilter = ref("");
const statusFilter = ref("");
const commandFilter = ref("");
const skillRunIdFilter = ref("");
const hoursFilter = ref(168);
const limit = ref(50);
const feedKey = ref(0);
const autoRefreshEnabled = ref(true);
const exporting = ref(false);

const toolOptions = builtinTools.map((tool) => ({ id: tool.id, name: tool.name }));

const statsHours = computed(() => (hoursFilter.value > 0 ? hoursFilter.value : undefined));

const activeSkillRunId = computed(() => skillRunIdFilter.value.trim() || undefined);

const exportQuery = computed(() => ({
  toolId: toolFilter.value || undefined,
  status: statusFilter.value || undefined,
  command: commandFilter.value.trim() || undefined,
  skillRunId: activeSkillRunId.value,
}));

function applyFilters() {
  feedKey.value += 1;
}

function applyRouteQuery() {
  const tool = route.query.tool;
  if (typeof tool === "string" && tool) {
    toolFilter.value = tool;
  }
  const skillRunId = route.query.skillRunId;
  if (typeof skillRunId === "string" && skillRunId) {
    skillRunIdFilter.value = skillRunId;
  }
}

async function exportLogs(format: "json" | "csv") {
  exporting.value = true;
  try {
    const logs = await fetchAllAgentToolLogs(props.agentSlug, exportQuery.value);
    if (format === "json") {
      downloadToolLogsJson(props.agentSlug, logs);
    } else {
      downloadToolLogsCsv(props.agentSlug, logs);
    }
  } finally {
    exporting.value = false;
  }
}

watch(
  () => route.query,
  () => applyRouteQuery(),
);

onMounted(() => {
  applyRouteQuery();
});
</script>

<template>
  <div class="mx-auto max-w-5xl">
    <div class="mb-6">
      <h2 class="text-2xl font-semibold">Tool logs</h2>
      <p class="mt-1 text-sm text-base-content/60">
        Единая лента всех вызовов Tools: Polza, Web Client, Telegram, LLM и др.
        Данные в Postgres — сохраняются между пересборками.
      </p>
    </div>

    <ToolLogStats
      :key="`stats-${feedKey}`"
      class="mb-4"
      :agent-slug="agentSlug"
      :tool-id="toolFilter || undefined"
      :skill-run-id="activeSkillRunId"
      :hours="statsHours"
    />

    <div class="mb-4 flex flex-wrap items-end gap-2 rounded-xl border border-base-300 bg-base-100 p-3">
      <label class="form-control min-w-[140px] gap-0.5">
        <span class="label-text text-xs">Tool</span>
        <select v-model="toolFilter" class="select select-bordered select-sm">
          <option value="">Все</option>
          <option v-for="tool in toolOptions" :key="tool.id" :value="tool.id">
            {{ tool.name }}
          </option>
        </select>
      </label>
      <label class="form-control min-w-[120px] gap-0.5">
        <span class="label-text text-xs">Статус</span>
        <select v-model="statusFilter" class="select select-bordered select-sm">
          <option value="">Все</option>
          <option value="ok">ok</option>
          <option value="error">error</option>
        </select>
      </label>
      <label class="form-control min-w-[120px] gap-0.5">
        <span class="label-text text-xs">Период</span>
        <select v-model.number="hoursFilter" class="select select-bordered select-sm">
          <option :value="24">24 ч</option>
          <option :value="168">7 дней</option>
          <option :value="720">30 дней</option>
          <option :value="0">Всё время</option>
        </select>
      </label>
      <label class="form-control min-w-[200px] flex-1 gap-0.5">
        <span class="label-text text-xs">skillRunId</span>
        <input
          v-model="skillRunIdFilter"
          class="input input-bordered input-sm font-mono"
          placeholder="фильтр по run…"
          @keyup.enter="applyFilters"
        />
      </label>
      <label class="form-control min-w-[160px] flex-1 gap-0.5">
        <span class="label-text text-xs">Command</span>
        <input
          v-model="commandFilter"
          class="input input-bordered input-sm"
          placeholder="send_message, run…"
          @keyup.enter="applyFilters"
        />
      </label>
      <label class="flex cursor-pointer items-center gap-2 self-end pb-1 text-xs">
        <input v-model="autoRefreshEnabled" type="checkbox" class="checkbox checkbox-sm" />
        авто ↻ 5s
      </label>
      <button type="button" class="btn btn-primary btn-sm" @click="applyFilters">
        Применить
      </button>
      <button
        type="button"
        class="btn btn-ghost btn-sm"
        :disabled="exporting"
        @click="exportLogs('json')"
      >
        {{ exporting ? "…" : "JSON" }}
      </button>
      <button
        type="button"
        class="btn btn-ghost btn-sm"
        :disabled="exporting"
        @click="exportLogs('csv')"
      >
        CSV
      </button>
    </div>

    <ToolLogFeed
      :key="`feed-${feedKey}`"
      :agent-slug="agentSlug"
      :tool-id="toolFilter || undefined"
      :skill-run-id="activeSkillRunId"
      :status="statusFilter || undefined"
      :command="commandFilter.trim() || undefined"
      :limit="limit"
      :auto-refresh-ms="autoRefreshEnabled ? 5000 : 0"
      :auto-refresh-default="autoRefreshEnabled"
      show-auto-refresh-toggle
      :show-header="false"
      empty-text="Пока нет записей. Логи появятся после вызовов Tools в runtime."
    />
  </div>
</template>
