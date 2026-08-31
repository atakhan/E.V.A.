<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import RuntimeHealthStrip from "@/features/runtime/components/RuntimeHealthStrip.vue";
import SkillRunTable from "@/features/runtime/components/SkillRunTable.vue";
import { useRuntimeSummary } from "@/features/runtime/composables/useRuntimeSummary";
import { useSkillRunList } from "@/features/runtime/composables/useSkillRunList";
import { cancelSkillRun } from "@/features/runtime/services/runtimeApi";
import type { SkillRunSummary } from "@/features/runtime/types/runtime";
import { agentRuntimePath, skillRunDetailPath } from "@/router/paths";

const router = useRouter();
const activeOnly = ref(true);
const actionError = ref<string | null>(null);

const { summary, metrics, loading, refreshing, error, reload } = useRuntimeSummary();
const { items, loading: runsLoading, refreshing: runsRefreshing, reload: reloadRuns } = useSkillRunList({
  statusFilter: ref("all"),
  activeOnly,
});

async function openRun(run: SkillRunSummary) {
  await router.push(skillRunDetailPath(run.agentSlug, run.skillRunId));
}

async function openAgentCockpit(slug: string) {
  await router.push(agentRuntimePath(slug));
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
</script>

<template>
  <main class="min-h-screen bg-base-200 px-6 py-10">
    <div class="mx-auto max-w-6xl space-y-6">
      <header class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 class="text-2xl font-semibold tracking-wide">Runtime Cockpit</h1>
          <p class="mt-1 text-sm text-base-content/60">
            Все агенты, активные skill runs и операционный срез runtime.
          </p>
        </div>
        <button type="button" class="btn btn-sm btn-ghost" @click="router.push('/agents')">
          ← Агенты
        </button>
      </header>

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
        :summary="summary"
        :metrics="metrics"
        :loading="loading"
        :refreshing="refreshing"
      />

      <section class="space-y-3">
        <h2 class="text-lg font-semibold">Агенты</h2>
        <div class="relative overflow-x-auto rounded-2xl border border-base-300 bg-base-100 shadow-sm">
          <span
            v-if="refreshing"
            class="absolute right-3 top-3 z-10 loading loading-spinner loading-xs text-base-content/40"
            aria-label="Обновление"
          />
          <table class="table table-sm">
            <thead>
              <tr class="text-xs uppercase tracking-wide text-base-content/50">
                <th>Agent</th>
                <th>Running</th>
                <th>Waiting</th>
                <th>Error</th>
                <th>Publication</th>
                <th class="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading && !summary?.agents.length">
                <td colspan="6" class="text-center text-sm text-base-content/50">Загрузка…</td>
              </tr>
              <tr v-else-if="!summary?.agents.length">
                <td colspan="6" class="text-center text-sm text-base-content/50">Нет агентов</td>
              </tr>
              <tr v-for="agent in summary?.agents ?? []" v-else :key="agent.agentSlug">
                <td class="font-mono text-xs">{{ agent.agentSlug }}</td>
                <td>{{ agent.running }}</td>
                <td>{{ agent.waiting }}</td>
                <td>{{ agent.error }}</td>
                <td class="font-mono text-xs">
                  {{ agent.isPublished ? `v${agent.latestPublicationVersion}` : "—" }}
                </td>
                <td class="text-right">
                  <button
                    type="button"
                    class="btn btn-xs btn-ghost"
                    @click="openAgentCockpit(agent.agentSlug)"
                  >
                    Открыть кокпит
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="space-y-3">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h2 class="text-lg font-semibold">Активные runs</h2>
          <button type="button" class="btn btn-xs btn-ghost" @click="reloadRuns()">
            Обновить
          </button>
        </div>
        <SkillRunTable
          :items="items"
          :loading="runsLoading"
          :refreshing="runsRefreshing"
          show-agent
          @open="openRun"
          @cancel="cancelRun"
        />
      </section>
    </div>
  </main>
</template>
