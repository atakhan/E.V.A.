<script setup lang="ts">
import { ref, useTemplateRef } from "vue";
import { useRouter } from "vue-router";
import AgentCard from "@/features/agents/components/AgentCard.vue";
import AgentFormDialog from "@/features/agents/components/AgentFormDialog.vue";
import { useAgents } from "@/features/agents/composables/useAgents";
import type { Agent } from "@/features/agents/types/agent";
import { agentHomePath } from "@/router/paths";

const router = useRouter();
const { agents, deleteAgent } = useAgents();

const createDialog = useTemplateRef("createDialog");
const editDialog = useTemplateRef("editDialog");
const editingAgent = ref<Agent | null>(null);

function openCreateForm() {
  createDialog.value?.open();
}

function openEditForm(agent: Agent) {
  editingAgent.value = agent;
  editDialog.value?.open();
}

async function openAgent(agent: Agent) {
  await router.push(agentHomePath(agent.slug));
}

function removeAgent(agent: Agent) {
  if (!confirm(`Удалить агента «${agent.name}»?`)) return;
  deleteAgent(agent.id);
  editDialog.value?.close();
}
</script>

<template>
  <main class="min-h-screen bg-base-200 px-6 py-10">
    <div class="mx-auto max-w-5xl">
      <header class="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 class="text-2xl font-semibold tracking-wide">E.V.A.</h1>
          <p class="mt-1 text-sm text-base-content/60">Engine for Versatile Agents</p>
          <p class="mt-3 text-base text-base-content/70">Агенты</p>
        </div>
        <button type="button" class="btn" @click="openCreateForm()">
          Новый агент
        </button>
      </header>

      <div
        v-if="agents.length === 0"
        class="rounded-2xl border border-dashed border-base-300 bg-base-100 px-6 py-16 text-center"
      >
        <p class="text-lg font-medium">Пока нет агентов</p>
        <p class="mt-2 text-sm text-base-content/60">
          Агент объединяет Skills, Actions и Tools конструктора
        </p>
        <button type="button" class="btn mt-6" @click="openCreateForm()">
          Создать агента
        </button>
      </div>

      <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <AgentCard
          v-for="agent in agents"
          :key="agent.id"
          :agent="agent"
          @open="openAgent(agent)"
          @edit="openEditForm(agent)"
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
