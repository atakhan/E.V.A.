<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useAgents } from "@/features/agents/composables/useAgents";
import { validateAgentApi } from "@/features/agents/services/agentsApi";
import { apiAvailable } from "@/features/agents/services/agentsStorage";
import {
  validateAgent,
  type AgentValidationReport,
} from "@/features/agents/utils/validateAgent";
import { useAgentRuntime } from "@/features/runtime/composables/useAgentRuntime";
import ToolLogFeed from "@/features/tools/components/ToolLogFeed.vue";
import { agentLogsPath, agentRuntimePath, skillRunDetailPath } from "@/router/paths";

const props = defineProps<{
  agentSlug: string;
}>();

const router = useRouter();
const { getAgentBySlug } = useAgents();
const agent = computed(() => getAgentBySlug(props.agentSlug));

const remoteReport = ref<AgentValidationReport | null>(null);

const {
  publications,
  latestPublication,
  isPublished,
  loadingPublications,
  publishing,
  running,
  error,
  activeRun,
  selectedSkillId,
  eventType,
  conversationId,
  messageText,
  entryEvents,
  followUpEvents,
  canContinueRun,
  loadPublications,
  resetRunForm,
  syncSkillSelection,
  publishDraft,
  sendEvent,
  newConversation,
} = useAgentRuntime(() => agent.value);

const localReport = computed(() => (agent.value ? validateAgent(agent.value) : null));
const report = computed(() => remoteReport.value ?? localReport.value);
const canPublish = computed(() => (report.value?.errors ?? 0) === 0 && !!agent.value?.skills.length);
const eventOptions = computed(() =>
  canContinueRun.value ? followUpEvents.value : entryEvents.value,
);

const statusBadgeClass = computed(() => {
  const status = activeRun.value?.status;
  if (status === "completed") return "badge-success";
  if (status === "waiting") return "badge-warning";
  if (status === "error") return "badge-error";
  return "badge-ghost";
});

async function loadValidation(slug: string) {
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
    resetRunForm(slug);
    void loadPublications(slug);
    void loadValidation(slug);
  },
  { immediate: true },
);

watch(agent, (value) => {
  if (value?.skills.length && !selectedSkillId.value) {
    resetRunForm(props.agentSlug);
  }
});

watch(selectedSkillId, () => {
  syncSkillSelection();
});

watch(eventOptions, (options) => {
  if (options.length && !options.includes(eventType.value)) {
    eventType.value = options[0];
  }
});

async function handlePublish() {
  const result = await publishDraft(props.agentSlug);
  if (result.ok) {
    await loadValidation(props.agentSlug);
  }
}

async function handleSend() {
  await sendEvent(props.agentSlug);
}

function handleNewConversation() {
  newConversation(props.agentSlug);
}

function openRunLogs() {
  if (!activeRun.value) return;
  void router.push(
    agentLogsPath(props.agentSlug, { skillRunId: activeRun.value.skillRunId }),
  );
}

function openInCockpit() {
  if (!activeRun.value) return;
  void router.push(skillRunDetailPath(props.agentSlug, activeRun.value.skillRunId));
}

function openRuntimeDashboard() {
  void router.push(agentRuntimePath(props.agentSlug));
}
</script>

<template>
  <section v-if="agent" class="space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold">Simulate</h2>
        <p class="mt-1 text-sm text-base-content/60">
          Dev sandbox: publish агента и отправьте тестовое событие в runtime.
        </p>
      </div>
      <button type="button" class="btn btn-sm btn-ghost" @click="openRuntimeDashboard">
        ← Runtime cockpit
      </button>
    </div>

    <div
      v-if="!apiAvailable"
      class="rounded-2xl border border-warning/40 bg-warning/5 px-5 py-4 text-sm text-warning"
    >
      Backend недоступен. Запустите
      <code class="font-mono text-xs">docker compose up</code>
      для publish и runtime.
    </div>

    <div class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 class="font-semibold">Публикация</h3>
          <p class="mt-1 text-sm text-base-content/60">
            Runtime исполняет последнюю опубликованную версию агента.
          </p>
        </div>
        <span
          class="badge"
          :class="isPublished ? 'badge-success badge-outline' : 'badge-ghost'"
        >
          {{ isPublished ? `v${latestPublication?.version}` : "не опубликован" }}
        </span>
      </div>

      <div v-if="loadingPublications" class="mt-4 text-sm text-base-content/50">
        Загрузка…
      </div>

      <div v-else class="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          class="btn btn-sm"
          :disabled="!apiAvailable || !canPublish || publishing"
          @click="handlePublish"
        >
          {{ publishing ? "Публикация…" : isPublished ? "Переопубликовать" : "Опубликовать" }}
        </button>
        <p v-if="!canPublish" class="text-sm text-error">
          Исправьте ошибки валидации и добавьте хотя бы один skill.
        </p>
        <p v-else-if="report" class="text-xs text-base-content/50">
          {{ report.errors }} errors · {{ report.warnings }} warnings
        </p>
      </div>

      <ul v-if="publications.length" class="mt-4 space-y-1 text-xs text-base-content/55">
        <li v-for="pub in publications.slice(0, 3)" :key="pub.id">
          v{{ pub.version }} · {{ new Date(pub.publishedAt).toLocaleString() }}
        </li>
      </ul>
    </div>

    <div
      v-if="isPublished && agent.skills.length"
      class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm"
    >
      <h3 class="font-semibold">
        {{ canContinueRun ? "Продолжить run" : "Новый run" }}
      </h3>
      <p class="mt-1 text-sm text-base-content/60">
        Симуляция входящего сообщения через entry-event skill.
      </p>

      <div class="mt-4 grid gap-4 lg:grid-cols-2">
        <label class="form-control w-full">
          <span class="label-text">Skill</span>
          <select
            v-model="selectedSkillId"
            class="select select-bordered select-sm w-full font-mono"
            :disabled="canContinueRun"
          >
            <option v-for="skill in agent.skills" :key="skill.id" :value="skill.id">
              {{ skill.name }} ({{ skill.id }})
            </option>
          </select>
        </label>

        <label class="form-control w-full">
          <span class="label-text">Event type</span>
          <select
            v-model="eventType"
            class="select select-bordered select-sm w-full font-mono"
          >
            <option v-for="evt in eventOptions" :key="evt" :value="evt">
              {{ evt }}
            </option>
          </select>
        </label>

        <label class="form-control w-full lg:col-span-2">
          <span class="label-text">conversation_id</span>
          <input
            v-model="conversationId"
            class="input input-bordered input-sm w-full font-mono"
            :readonly="canContinueRun"
          />
        </label>

        <label class="form-control w-full lg:col-span-2">
          <span class="label-text">Текст сообщения</span>
          <textarea
            v-model="messageText"
            class="textarea textarea-bordered textarea-sm w-full"
            rows="3"
            placeholder="Нужны грибки на объект срочно"
          />
        </label>
      </div>

      <div class="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          class="btn btn-sm btn-primary"
          :disabled="running || !messageText.trim()"
          @click="handleSend"
        >
          {{ running ? "Отправка…" : canContinueRun ? "Отправить ответ" : "Запустить" }}
        </button>
        <button
          type="button"
          class="btn btn-sm btn-ghost"
          :disabled="running"
          @click="handleNewConversation"
        >
          Новый диалог
        </button>
      </div>
    </div>

    <div
      v-if="error"
      class="rounded-xl border border-error/40 bg-error/5 px-4 py-3 text-sm text-error"
    >
      {{ error }}
    </div>

    <div
      v-if="activeRun"
      class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm"
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 class="font-semibold">Skill run</h3>
          <p class="mt-1 font-mono text-xs text-base-content/50">
            {{ activeRun.skillRunId }}
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <span class="badge" :class="statusBadgeClass">{{ activeRun.status }}</span>
          <span class="badge badge-outline font-mono">{{ activeRun.currentState }}</span>
          <button type="button" class="btn btn-xs btn-ghost" @click="openInCockpit">
            Открыть в кокпите →
          </button>
        </div>
      </div>

      <div class="mt-4">
        <p class="text-xs font-semibold uppercase tracking-wide text-base-content/50">History</p>
        <div class="mt-2 flex flex-wrap gap-1">
          <span
            v-for="(state, index) in activeRun.history"
            :key="`${state}-${index}`"
            class="badge badge-sm font-mono"
            :class="index === activeRun.history.length - 1 ? 'badge-primary' : 'badge-ghost'"
          >
            {{ state }}
          </span>
        </div>
      </div>

      <div class="mt-5 border-t border-base-300/60 pt-4">
        <div class="mb-2 flex items-center justify-between gap-2">
          <p class="text-xs font-semibold uppercase tracking-wide text-base-content/50">
            Tool logs этого run
          </p>
          <button type="button" class="btn btn-ghost btn-xs" @click="openRunLogs">
            Все логи run →
          </button>
        </div>
        <ToolLogFeed
          :agent-slug="agentSlug"
          :skill-run-id="activeRun.skillRunId"
          :limit="20"
          compact
          :show-header="true"
          :auto-refresh-ms="5000"
          auto-refresh-default
        />
      </div>
    </div>
  </section>
</template>
