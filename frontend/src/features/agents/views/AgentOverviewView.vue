<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useAgents } from "@/features/agents/composables/useAgents";
import { validateAgentApi } from "@/features/agents/services/agentsApi";
import { apiAvailable } from "@/features/agents/services/agentsStorage";
import {
  actionUsageCount,
  validateAgent,
  type AgentIssueSeverity,
  type AgentValidationReport,
} from "@/features/agents/utils/validateAgent";
import { agentRunPath, agentSkillsPath, agentActionsPath, agentToolsPath, skillPath } from "@/router/paths";

const props = defineProps<{
  agentSlug: string;
}>();

const router = useRouter();
const { getAgentBySlug } = useAgents();
const agent = computed(() => getAgentBySlug(props.agentSlug));
const remoteReport = ref<AgentValidationReport | null>(null);

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
    void loadRemoteReport(slug);
  },
  { immediate: true },
);

const report = computed(() =>
  remoteReport.value ?? (agent.value ? validateAgent(agent.value) : null),
);

const enabledTools = computed(() =>
  agent.value ? agent.value.tools.filter((tool) => tool.enabled) : [],
);

const isEmpty = computed(
  () =>
    !!agent.value &&
    agent.value.skills.length === 0 &&
    agent.value.actions.length === 0 &&
    enabledTools.value.length === 0,
);

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
</script>

<template>
  <section v-if="agent" class="space-y-6">
    <div>
      <h2 class="text-lg font-semibold">Overview</h2>
      <p class="mt-1 text-sm text-base-content/60">
        Связность конструктора: Skills → Actions → Tools
      </p>
    </div>

    <div class="grid gap-4 sm:grid-cols-3">
      <button
        type="button"
        class="rounded-2xl border border-base-300 bg-base-100 p-5 text-left shadow-sm transition hover:border-primary/40 hover:shadow-md"
        @click="router.push(agentSkillsPath(agent.slug))"
      >
        <p class="text-xs font-semibold uppercase tracking-wide text-base-content/50">Skills</p>
        <p class="mt-2 text-3xl font-semibold">{{ agent.skills.length }}</p>
        <p class="mt-2 text-sm text-base-content/60">Процессы с FSM</p>
      </button>

      <button
        type="button"
        class="rounded-2xl border border-base-300 bg-base-100 p-5 text-left shadow-sm transition hover:border-primary/40 hover:shadow-md"
        @click="router.push(agentActionsPath(agent.slug))"
      >
        <p class="text-xs font-semibold uppercase tracking-wide text-base-content/50">Actions</p>
        <p class="mt-2 text-3xl font-semibold">{{ agent.actions.length }}</p>
        <p class="mt-2 text-sm text-base-content/60">Поступки и recipe</p>
      </button>

      <button
        type="button"
        class="rounded-2xl border border-base-300 bg-base-100 p-5 text-left shadow-sm transition hover:border-primary/40 hover:shadow-md"
        @click="router.push(agentToolsPath(agent.slug))"
      >
        <p class="text-xs font-semibold uppercase tracking-wide text-base-content/50">Tools</p>
        <p class="mt-2 text-3xl font-semibold">{{ enabledTools.length }}</p>
        <p class="mt-2 text-sm text-base-content/60">
          Подключено
          <span v-if="agent.tools.length !== enabledTools.length">
            / {{ agent.tools.length }} в bindings
          </span>
        </p>
      </button>
    </div>

    <div
      v-if="report && report.errors === 0 && agent.skills.length"
      class="rounded-2xl border border-primary/30 bg-primary/5 p-5 shadow-sm"
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 class="font-semibold">Готов к запуску</h3>
          <p class="mt-1 text-sm text-base-content/60">
            Опубликуйте агента и отправьте тестовое событие в runtime.
          </p>
        </div>
        <button
          type="button"
          class="btn btn-sm btn-primary"
          @click="router.push(agentRunPath(agent.slug))"
        >
          Run
        </button>
      </div>
    </div>

    <div
      v-if="report"
      class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm"
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 class="font-semibold">Проверка конструктора</h3>
          <p class="mt-1 text-sm text-base-content/60">
            Без runtime: ссылки, initial, recipe и подключённые Tools
          </p>
        </div>
        <div class="flex flex-wrap gap-2 text-xs">
          <span class="badge badge-error badge-outline">{{ report.errors }} errors</span>
          <span class="badge badge-warning badge-outline">{{ report.warnings }} warnings</span>
          <span class="badge badge-ghost">{{ report.infos }} info</span>
        </div>
      </div>

      <div
        v-if="report.issues.length === 0"
        class="mt-4 rounded-xl border border-success/30 bg-success/5 px-4 py-3 text-sm text-success"
      >
        Замечаний нет — модель согласована.
      </div>

      <ul v-else class="mt-4 space-y-2">
        <li
          v-for="issue in report.issues"
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
    </div>

    <div
      v-if="isEmpty"
      class="rounded-2xl border border-dashed border-base-300 bg-base-100 px-6 py-10 text-center"
    >
      <p class="font-medium">Агент пока пустой</p>
      <p class="mt-2 text-sm text-base-content/60">
        Подключите Tools, опишите Actions и соберите Skill на холсте.
      </p>
      <div class="mt-4 flex flex-wrap justify-center gap-2">
        <button type="button" class="btn btn-sm" @click="router.push(agentToolsPath(agent.slug))">
          Tools
        </button>
        <button type="button" class="btn btn-sm" @click="router.push(agentActionsPath(agent.slug))">
          Actions
        </button>
        <button type="button" class="btn btn-sm" @click="router.push(agentSkillsPath(agent.slug))">
          Skills
        </button>
      </div>
    </div>

    <div v-else class="grid gap-4 lg:grid-cols-3">
      <section class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
        <div class="mb-3 flex items-center justify-between gap-2">
          <h3 class="font-semibold">Skills</h3>
          <button
            type="button"
            class="btn btn-ghost btn-xs"
            @click="router.push(agentSkillsPath(agent.slug))"
          >
            Все
          </button>
        </div>
        <ul v-if="agent.skills.length" class="space-y-2">
          <li v-for="skill in agent.skills" :key="skill.id">
            <button
              type="button"
              class="w-full rounded-lg border border-base-300 bg-base-200/30 px-3 py-2 text-left transition hover:border-primary/40"
              @click="router.push(skillPath(agent.slug, skill.id))"
            >
              <p class="truncate font-medium">{{ skill.name }}</p>
              <p class="mt-1 font-mono text-[11px] text-base-content/50">
                {{ skill.states.length }} states · initial
                {{ skill.initial ?? "—" }}
              </p>
            </button>
          </li>
        </ul>
        <p v-else class="text-sm text-base-content/50">Пока нет</p>
      </section>

      <section class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
        <div class="mb-3 flex items-center justify-between gap-2">
          <h3 class="font-semibold">Actions</h3>
          <button
            type="button"
            class="btn btn-ghost btn-xs"
            @click="router.push(agentActionsPath(agent.slug))"
          >
            Все
          </button>
        </div>
        <ul v-if="agent.actions.length" class="space-y-2">
          <li
            v-for="action in agent.actions"
            :key="action.id"
            class="rounded-lg border border-base-300 bg-base-200/30 px-3 py-2"
          >
            <p class="truncate font-medium">{{ action.name }}</p>
            <p class="mt-1 font-mono text-[11px] text-base-content/50">
              {{ action.id }} · {{ action.recipe.length }} steps ·
              used {{ actionUsageCount(agent, action.id) }}
            </p>
          </li>
        </ul>
        <p v-else class="text-sm text-base-content/50">Пока нет</p>
      </section>

      <section class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
        <div class="mb-3 flex items-center justify-between gap-2">
          <h3 class="font-semibold">Tools</h3>
          <button
            type="button"
            class="btn btn-ghost btn-xs"
            @click="router.push(agentToolsPath(agent.slug))"
          >
            Все
          </button>
        </div>
        <ul v-if="enabledTools.length" class="space-y-2">
          <li
            v-for="tool in enabledTools"
            :key="tool.id"
            class="rounded-lg border border-base-300 bg-base-200/30 px-3 py-2"
          >
            <p class="font-mono text-sm">{{ tool.toolId }}</p>
            <p v-if="tool.configNote" class="mt-1 line-clamp-2 text-[11px] text-base-content/50">
              {{ tool.configNote }}
            </p>
          </li>
        </ul>
        <p v-else class="text-sm text-base-content/50">Нет подключённых Tools</p>
      </section>
    </div>
  </section>
</template>
