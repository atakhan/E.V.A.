<script setup lang="ts">
import { computed, ref, toRef, useTemplateRef, watch } from "vue";
import { useRouter } from "vue-router";
import AgentFormDialog from "@/features/agents/components/AgentFormDialog.vue";
import AgentReadinessChecklist from "@/features/agents/components/AgentReadinessChecklist.vue";
import { useAgentOverview } from "@/features/agents/composables/useAgentOverview";
import { useAgents } from "@/features/agents/composables/useAgents";
import { validateAgentApi } from "@/features/agents/services/agentsApi";
import { apiAvailable } from "@/features/agents/services/agentsStorage";
import {
  validateAgent,
  type AgentIssueSeverity,
  type AgentValidationReport,
} from "@/features/agents/utils/validateAgent";
import { formatDateTime } from "@/shared/utils/formatDate";

const props = defineProps<{
  agentSlug: string;
}>();

const router = useRouter();
const { getAgentBySlug } = useAgents();
const editDialog = useTemplateRef("editDialog");
const agentSlugRef = toRef(props, "agentSlug");

const agent = computed(() => getAgentBySlug(props.agentSlug));
const remoteReport = ref<AgentValidationReport | null>(null);
const showInfoIssues = ref(false);
const publishMessage = ref<string | null>(null);

async function loadRemoteReport(slug: string) {
  if (!apiAvailable.value) {
    remoteReport.value = null;
    return;
  }
  try {
    remoteReport.value = await validateAgentApi(slug);
  } catch {
    remoteReport.value = null;
  }
}

watch(
  () => props.agentSlug,
  (slug) => {
    publishMessage.value = null;
    void loadRemoteReport(slug);
  },
  { immediate: true },
);

const report = computed(
  () => remoteReport.value ?? (agent.value ? validateAgent(agent.value) : null),
);

const {
  latestPublication,
  isPublished,
  loadingPublications,
  publishing,
  agentSummary,
  runtimeSummaryLoading,
  ingressBadges,
  readinessItems,
  readinessProgress,
  canPublish,
  blockingIssues,
  infoIssues,
  handlePublish,
  agentRuntimePath,
  agentRuntimeSimulatePath,
  error: runtimeError,
} = useAgentOverview({
  agentSlug: agentSlugRef,
  agent,
  report,
});

function severityClass(severity: AgentIssueSeverity): string {
  if (severity === "error") return "border-error/40 bg-error/5 text-error";
  if (severity === "warning") return "border-warning/40 bg-warning/5 text-warning";
  return "border-base-300 bg-base-200/40 text-base-content/70";
}

function severityLabel(severity: AgentIssueSeverity): string {
  if (severity === "error") return "error";
  if (severity === "warning") return "warning";
  return "info";
}

async function onPublish() {
  publishMessage.value = null;
  const result = await handlePublish();
  if (result.ok) {
    publishMessage.value = `Опубликовано v${result.version}`;
    await loadRemoteReport(props.agentSlug);
  } else if (result.error) {
    publishMessage.value = result.error;
  }
}
</script>

<template>
  <section v-if="agent" class="space-y-6">
    <div class="rounded-2xl border border-base-300 bg-base-100 p-6 shadow-sm">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="min-w-0 flex-1">
          <p class="text-xs font-semibold uppercase tracking-wide text-base-content/50">Агент</p>
          <h2 class="mt-1 text-2xl font-semibold">{{ agent.name }}</h2>
          <p class="mt-2 font-mono text-sm text-base-content/55">/{{ agent.slug }}</p>
          <p
            v-if="agent.description"
            class="mt-3 max-w-2xl text-sm leading-relaxed text-base-content/75"
          >
            {{ agent.description }}
          </p>
          <p v-else class="mt-3 text-sm italic text-base-content/45">Описание не задано</p>
          <p class="mt-3 text-xs text-base-content/45">
            Создан {{ formatDateTime(agent.createdAt) }} · обновлён
            {{ formatDateTime(agent.updatedAt) }}
          </p>
        </div>
        <button
          type="button"
          class="btn btn-sm btn-ghost"
          @click="editDialog?.open()"
        >
          Редактировать
        </button>
      </div>
    </div>

    <div class="flex flex-wrap gap-2">
      <span
        class="badge badge-lg"
        :class="isPublished ? 'badge-success badge-outline' : 'badge-ghost'"
      >
        {{ isPublished ? `v${latestPublication?.version}` : "Черновик" }}
      </span>

      <template v-if="report">
        <span
          class="badge badge-lg"
          :class="report.errors ? 'badge-error badge-outline' : 'badge-ghost'"
        >
          {{ report.errors }} errors
        </span>
        <span
          class="badge badge-lg"
          :class="report.warnings ? 'badge-warning badge-outline' : 'badge-ghost'"
        >
          {{ report.warnings }} warnings
        </span>
      </template>

      <template v-if="agentSummary && !runtimeSummaryLoading">
        <span
          v-if="agentSummary.running"
          class="badge badge-lg badge-primary badge-outline"
        >
          {{ agentSummary.running }} running
        </span>
        <span
          v-if="agentSummary.waiting"
          class="badge badge-lg badge-info badge-outline"
        >
          {{ agentSummary.waiting }} waiting
        </span>
        <span
          v-if="agentSummary.error"
          class="badge badge-lg badge-error badge-outline"
        >
          {{ agentSummary.error }} run errors
        </span>
      </template>
      <span v-else-if="runtimeSummaryLoading" class="badge badge-lg badge-ghost">
        runtime…
      </span>

      <span
        v-for="ingress in ingressBadges"
        :key="ingress.toolId"
        class="badge badge-lg"
        :class="ingress.active ? 'badge-success badge-outline' : 'badge-ghost'"
      >
        {{ ingress.label }} {{ ingress.active ? "✓" : "—" }}
      </span>
    </div>

    <AgentReadinessChecklist :items="readinessItems" :progress="readinessProgress" />

    <div class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 class="font-semibold">Действия</h3>
          <p class="mt-1 text-sm text-base-content/60">
            Публикация, симуляция и операционный кокпит
          </p>
        </div>
      </div>

      <div
        v-if="!apiAvailable"
        class="mt-4 rounded-xl border border-warning/40 bg-warning/5 px-4 py-3 text-sm text-warning"
      >
        Backend недоступен. Запустите
        <code class="font-mono text-xs">docker compose up</code>
        для publish и runtime.
      </div>

      <div class="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          class="btn btn-primary btn-sm"
          :disabled="!apiAvailable || !canPublish || publishing"
          @click="onPublish"
        >
          {{
            publishing
              ? "Публикация…"
              : isPublished
                ? "Переопубликовать"
                : "Опубликовать"
          }}
        </button>
        <button
          type="button"
          class="btn btn-sm"
          @click="router.push(agentRuntimeSimulatePath())"
        >
          Simulate
        </button>
        <button
          type="button"
          class="btn btn-sm btn-ghost"
          @click="router.push(agentRuntimePath())"
        >
          Runtime
        </button>
      </div>

      <p v-if="!canPublish" class="mt-3 text-sm text-error">
        Исправьте ошибки валидации и добавьте хотя бы один skill.
      </p>
      <p v-else-if="publishMessage" class="mt-3 text-sm text-success">{{ publishMessage }}</p>
      <p v-else-if="runtimeError" class="mt-3 text-sm text-error">{{ runtimeError }}</p>
      <p v-else-if="loadingPublications" class="mt-3 text-xs text-base-content/50">
        Загрузка публикаций…
      </p>
    </div>

    <div
      v-if="report"
      class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm"
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 class="font-semibold">Проверка конструктора</h3>
          <p class="mt-1 text-sm text-base-content/60">
            Ссылки, initial, recipe и подключённые Tools
          </p>
        </div>
        <div class="flex flex-wrap gap-2 text-xs">
          <span class="badge badge-error badge-outline">{{ report.errors }} errors</span>
          <span class="badge badge-warning badge-outline">{{ report.warnings }} warnings</span>
          <span v-if="report.infos" class="badge badge-ghost">{{ report.infos }} info</span>
        </div>
      </div>

      <div
        v-if="report.issues.length === 0"
        class="mt-4 rounded-xl border border-success/30 bg-success/5 px-4 py-3 text-sm text-success"
      >
        Замечаний нет — модель согласована.
      </div>

      <template v-else>
        <ul v-if="blockingIssues.length" class="mt-4 space-y-2">
          <li
            v-for="issue in blockingIssues"
            :key="issue.id"
            class="rounded-xl border px-3 py-2 text-sm"
            :class="severityClass(issue.severity)"
          >
            <div class="flex flex-wrap items-start justify-between gap-2">
              <div class="min-w-0">
                <span class="badge badge-xs mr-2 uppercase opacity-80">
                  {{ severityLabel(issue.severity) }}
                </span>
                <span>{{ issue.message }}</span>
              </div>
              <button
                v-if="issue.href"
                type="button"
                class="btn btn-ghost btn-xs shrink-0"
                @click="router.push(issue.href)"
              >
                Открыть
              </button>
            </div>
          </li>
        </ul>

        <div v-if="infoIssues.length" class="mt-4">
          <button
            type="button"
            class="btn btn-ghost btn-xs"
            @click="showInfoIssues = !showInfoIssues"
          >
            {{ showInfoIssues ? "Скрыть" : "Показать" }} info ({{ infoIssues.length }})
          </button>
          <ul v-if="showInfoIssues" class="mt-2 space-y-2">
            <li
              v-for="issue in infoIssues"
              :key="issue.id"
              class="rounded-xl border px-3 py-2 text-sm"
              :class="severityClass(issue.severity)"
            >
              <div class="flex flex-wrap items-start justify-between gap-2">
                <div class="min-w-0">
                  <span class="badge badge-xs mr-2 uppercase opacity-80">info</span>
                  <span>{{ issue.message }}</span>
                </div>
                <button
                  v-if="issue.href"
                  type="button"
                  class="btn btn-ghost btn-xs shrink-0"
                  @click="router.push(issue.href)"
                >
                  Открыть
                </button>
              </div>
            </li>
          </ul>
        </div>
      </template>
    </div>

    <AgentFormDialog ref="editDialog" mode="edit" :agent="agent" />
  </section>
</template>
