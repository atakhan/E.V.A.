<script setup lang="ts">
import { computed, onMounted, ref, useTemplateRef, watch } from "vue";
import { useRouter } from "vue-router";
import AgentCard from "@/features/agents/components/AgentCard.vue";
import AgentFormDialog from "@/features/agents/components/AgentFormDialog.vue";
import { useAgents } from "@/features/agents/composables/useAgents";
import type { Agent } from "@/features/agents/types/agent";
import EvaBrand from "@/shared/components/EvaBrand.vue";
import { agentHomePath, agentRuntimePath, globalRuntimePath, toolsLibraryPath } from "@/router/paths";

const router = useRouter();
const {
  activeAgents,
  deleteAgent,
  archiveAgent,
  unarchiveAgent,
  fetchArchivedAgentSummaries,
} = useAgents();

const tab = ref<"active" | "archive">("active");
const archivedAgents = ref<Agent[]>([]);
const archiveLoading = ref(false);

const createDialog = useTemplateRef("createDialog");
const editDialog = useTemplateRef("editDialog");
const editingAgent = ref<Agent | null>(null);

const visibleAgents = computed(() => (tab.value === "active" ? activeAgents.value : archivedAgents.value));

async function loadArchivedAgents() {
  archiveLoading.value = true;
  try {
    archivedAgents.value = await fetchArchivedAgentSummaries();
  } finally {
    archiveLoading.value = false;
  }
}

watch(tab, (value) => {
  if (value === "archive") {
    void loadArchivedAgents();
  }
});

onMounted(() => {
  if (tab.value === "archive") {
    void loadArchivedAgents();
  }
});

function openCreateForm() {
  createDialog.value?.open();
}

function openEditForm(agent: Agent) {
  editingAgent.value = agent;
  editDialog.value?.open();
}

async function openAgent(agent: Agent) {
  if (agent.archivedAt) {
    await router.push(agentRuntimePath(agent.slug));
    return;
  }
  await router.push(agentHomePath(agent.slug));
}

async function openGlobalRuntime() {
  await router.push(globalRuntimePath());
}

function removeAgent(agent: Agent) {
  if (!confirm(`Удалить агента «${agent.name}»? История runs останется в базе.`)) return;
  deleteAgent(agent.id);
  archivedAgents.value = archivedAgents.value.filter((item) => item.id !== agent.id);
  editDialog.value?.close();
}

async function archiveAgentAction(agent: Agent) {
  if (
    !confirm(
      `Архивировать агента «${agent.name}»? Новые запуски и ingress будут заблокированы, активные runs отменятся.`,
    )
  ) {
    return;
  }
  const result = await archiveAgent(agent.id);
  if (!result.ok) {
    alert(result.error);
    return;
  }
  if (tab.value === "archive") {
    await loadArchivedAgents();
  }
}

async function unarchiveAgentAction(agent: Agent) {
  const result = await unarchiveAgent(agent.id);
  if (!result.ok) {
    alert(result.error);
    return;
  }
  archivedAgents.value = archivedAgents.value.filter((item) => item.id !== agent.id);
}
</script>

<template>
  <main class="min-h-screen bg-base-200 px-6 py-10">
    <div class="mx-auto max-w-5xl">
      <header class="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <EvaBrand />
          <p class="mt-3 text-base text-base-content/70">Агенты</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button type="button" class="btn btn-ghost" @click="openGlobalRuntime()">
            Runtime
          </button>
          <button type="button" class="btn btn-ghost" @click="router.push(toolsLibraryPath())">
            Библиотека Tools
          </button>
          <button type="button" class="btn" @click="openCreateForm()">
            Новый агент
          </button>
        </div>
      </header>

      <div role="tablist" class="tabs tabs-boxed mb-6 w-fit">
        <button
          type="button"
          role="tab"
          class="tab"
          :class="{ 'tab-active': tab === 'active' }"
          @click="tab = 'active'"
        >
          Активные
        </button>
        <button
          type="button"
          role="tab"
          class="tab"
          :class="{ 'tab-active': tab === 'archive' }"
          @click="tab = 'archive'"
        >
          Архив
        </button>
      </div>

      <div
        v-if="archiveLoading"
        class="rounded-2xl border border-base-300 bg-base-100 px-6 py-16 text-center text-sm text-base-content/60"
      >
        Загрузка архива…
      </div>

      <div
        v-else-if="visibleAgents.length === 0"
        class="rounded-2xl border border-dashed border-base-300 bg-base-100 px-6 py-16 text-center"
      >
        <p class="text-lg font-medium">
          {{ tab === "active" ? "Пока нет агентов" : "Архив пуст" }}
        </p>
        <p class="mt-2 text-sm text-base-content/60">
          {{
            tab === "active"
              ? "Агент объединяет Skills, Actions и Tools конструктора"
              : "Архивированные агенты скрыты из runtime, но история runs сохраняется"
          }}
        </p>
        <button
          v-if="tab === 'active'"
          type="button"
          class="btn mt-6"
          @click="openCreateForm()"
        >
          Создать агента
        </button>
      </div>

      <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <AgentCard
          v-for="agent in visibleAgents"
          :key="agent.id"
          :agent="agent"
          :archived="tab === 'archive'"
          @open="openAgent(agent)"
          @edit="openEditForm(agent)"
          @archive="archiveAgentAction(agent)"
          @unarchive="unarchiveAgentAction(agent)"
          @remove="removeAgent(agent)"
        />
      </div>
    </div>

    <AgentFormDialog ref="createDialog" mode="create" />
    <AgentFormDialog
      ref="editDialog"
      mode="edit"
      :agent="editingAgent"
    />
  </main>
</template>
