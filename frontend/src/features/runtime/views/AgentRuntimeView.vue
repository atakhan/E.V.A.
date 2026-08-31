<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useAgents } from "@/features/agents/composables/useAgents";
import RuntimeHealthStrip from "@/features/runtime/components/RuntimeHealthStrip.vue";
import SkillRunTable from "@/features/runtime/components/SkillRunTable.vue";
import { useRuntimeSummary } from "@/features/runtime/composables/useRuntimeSummary";
import { useSkillRunList } from "@/features/runtime/composables/useSkillRunList";
import { cancelSkillRun } from "@/features/runtime/services/runtimeApi";
import type { SkillRunStatusFilter, SkillRunSummary } from "@/features/runtime/types/runtime";
import { agentRuntimeSimulatePath, skillRunDetailPath } from "@/router/paths";

const props = defineProps<{
  agentSlug: string;
}>();

const router = useRouter();
const { getAgentBySlug, unarchiveAgent } = useAgents();
const agent = computed(() => getAgentBySlug(props.agentSlug));

const statusFilter = ref<SkillRunStatusFilter>("active");
const selectedSkillId = ref("");
const actionError = ref<string | null>(null);

const agentSlugRef = computed(() => props.agentSlug);
const skillIdRef = computed(() => selectedSkillId.value || undefined);

const { agentSummary, metrics, loading, refreshing, error, reload } = useRuntimeSummary({
  agentSlug: agentSlugRef,
});
const { items, total, loading: runsLoading, refreshing: runsRefreshing, reload: reloadRuns } = useSkillRunList({
  agentSlug: agentSlugRef,
  statusFilter,
  skillId: skillIdRef,
});

const isArchived = computed(() => Boolean(agent.value?.archivedAt || agentSummary.value?.archived));

const statusTabs: Array<{ id: SkillRunStatusFilter; label: string }> = [
  { id: "active", label: "Active" },
  { id: "waiting", label: "Waiting" },
  { id: "completed", label: "Completed" },
  { id: "error", label: "Failed" },
  { id: "all", label: "All" },
];

async function openRun(run: SkillRunSummary) {
  await router.push(skillRunDetailPath(props.agentSlug, run.skillRunId));
}

async function openSimulate() {
  await router.push(agentRuntimeSimulatePath(props.agentSlug));
}

async function cancelRun(run: SkillRunSummary) {
  if (!confirm(`Отменить run ${run.skillRunId}?`)) return;
  actionError.value = null;
  try {
    await cancelSkillRun(run.skillRunId);
    await Promise.all([reload(), reloadRuns()]);
  } catch (cancelError) {
    actionError.value =
      cancelError instanceof Error ? cancelError.message : "Не удалось отменить run";
  }
}

async function restoreAgent() {
  if (!agent.value) return;
  const result = await unarchiveAgent(agent.value.id);
  if (!result.ok) {
    alert(result.error);
  }
}
</script>

<template>
  <section v-if="agent" class="space-y-6">
    <div
      v-if="isArchived"
      class="alert alert-warning"
    >
      <div>
        <p class="font-medium">Агент в архиве</p>
        <p class="text-sm opacity-80">
          Новые запуски и ingress заблокированы. Доступна только история runs.
        </p>
      </div>
      <button type="button" class="btn btn-sm" @click="restoreAgent()">
        Восстановить
      </button>
    </div>

    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold">Runtime</h2>
        <p class="mt-1 text-sm text-base-content/60">
          Операционный кокпит агента: активные runs, статусы и история исполнения.
        </p>
      </div>
      <button v-if="!isArchived" type="button" class="btn btn-sm" @click="openSimulate()">
        Simulate event
      </button>
    </div>

    <p v-if="error" class="rounded-xl border border-error/40 bg-error/5 px-4 py-3 text-sm text-error">
      {{ error }}
    </p>
    <p
      v-if="actionError"
      class="rounded-xl border border-error/40 bg-error/5 px-4 py-3 text-sm text-error"
    >
      {{ actionError }}
    </p>

    <RuntimeHealthStrip
      :agent-summary="agentSummary"
      :metrics="metrics"
      :loading="loading"
      :refreshing="refreshing"
    />

    <div class="flex flex-wrap items-center gap-2">
      <button
        v-for="tab in statusTabs"
        :key="tab.id"
        type="button"
        class="btn btn-xs"
        :class="statusFilter === tab.id ? 'btn-active' : 'btn-ghost'"
        @click="statusFilter = tab.id"
      >
        {{ tab.label }}
      </button>

      <select
        v-model="selectedSkillId"
        class="select select-bordered select-xs ml-auto max-w-xs font-mono"
      >
        <option value="">Все skills</option>
        <option v-for="skill in agent.skills" :key="skill.id" :value="skill.id">
          {{ skill.name }} ({{ skill.id }})
        </option>
      </select>
    </div>

    <div class="flex items-center justify-between gap-3 text-sm text-base-content/60">
      <span>{{ total }} run(s)</span>
      <button type="button" class="btn btn-xs btn-ghost" @click="reloadRuns()">Обновить</button>
    </div>

    <SkillRunTable
      :items="items"
      :loading="runsLoading"
      :refreshing="runsRefreshing"
      @open="openRun"
      @cancel="cancelRun"
    />

    <div
      v-if="!runsLoading && !items.length"
      class="rounded-2xl border border-dashed border-base-300 px-6 py-10 text-center"
    >
      <p class="text-sm text-base-content/60">Нет runs для выбранного фильтра</p>
      <button v-if="!isArchived" type="button" class="btn btn-sm mt-4" @click="openSimulate()">
        Запустить simulate
      </button>
    </div>
  </section>
</template>
