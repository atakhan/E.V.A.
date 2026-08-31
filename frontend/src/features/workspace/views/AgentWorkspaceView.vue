<script setup lang="ts">
import { computed, useTemplateRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import AgentFormDialog from "@/features/agents/components/AgentFormDialog.vue";
import { useAgents } from "@/features/agents/composables/useAgents";
import EvaBrand from "@/shared/components/EvaBrand.vue";
import WorkspaceSidebar from "@/features/workspace/components/WorkspaceSidebar.vue";
import {
  defaultWorkspaceSectionId,
  findWorkspaceSection,
  workspaceSections,
} from "@/features/workspace/config/nav";
import { agentSectionPath, agentsPath, RouteNames } from "@/router/paths";

const props = defineProps<{
  agentSlug: string;
}>();

const route = useRoute();
const router = useRouter();
const { getAgentBySlug } = useAgents();
const editDialog = useTemplateRef("editDialog");

const agent = computed(() => getAgentBySlug(props.agentSlug));

const activeSectionId = computed(() => {
  const leaf = String(route.name ?? "");
  if (leaf === RouteNames.skillCanvas || leaf.includes("skills")) return "skills";
  if (leaf.includes("actions")) return "actions";
  if (leaf.includes("tools")) return "tools";
  if (leaf.includes("logs")) return "logs";
  if (leaf.includes("runtime") || leaf === RouteNames.agentRuntimeSimulate || leaf === RouteNames.skillRunDetail) {
    return "runtime";
  }
  if (leaf.includes("run")) return "runtime";
  if (leaf.includes("overview")) return "overview";

  const pathPart = route.path.split("/").filter(Boolean)[1];
  return findWorkspaceSection(pathPart ?? "")?.id ?? defaultWorkspaceSectionId;
});

const isSkillCanvas = computed(() => route.name === RouteNames.skillCanvas);

async function selectSection(id: string) {
  if (!agent.value) return;
  const section = findWorkspaceSection(id);
  if (!section) return;
  await router.push(agentSectionPath(agent.value.slug, section.slug));
}

async function goToAgents() {
  await router.push(agentsPath());
}
</script>

<template>
  <div v-if="agent" class="flex h-screen min-h-0 bg-base-200">
    <aside class="flex w-64 shrink-0 flex-col border-r border-base-300 bg-base-100">
      <div class="border-b border-base-300 px-4 py-4">
        <button
          type="button"
          class="mb-3 block w-full rounded-lg text-left transition-colors hover:bg-base-200"
          @click="goToAgents()"
        >
          <EvaBrand size="sm" :show-tagline="false" title-class="text-base" />
        </button>

        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <h1 class="truncate text-lg font-semibold">{{ agent.name }}</h1>
            <p class="mt-1 font-mono text-xs text-base-content/50">/{{ agent.slug }}</p>
            <p
              v-if="agent.description"
              class="mt-1 line-clamp-2 text-xs text-base-content/60"
            >
              {{ agent.description }}
            </p>
          </div>
          <button
            type="button"
            class="btn btn-xs btn-square btn-ghost shrink-0"
            title="Редактировать агента"
            aria-label="Редактировать агента"
            @click="editDialog?.open()"
          >
            ✎
          </button>
        </div>
      </div>

      <WorkspaceSidebar
        :sections="workspaceSections"
        :active-id="activeSectionId"
        @select="selectSection"
      />
    </aside>

    <main
      class="flex min-h-0 min-w-0 flex-1 flex-col"
      :class="isSkillCanvas ? 'overflow-hidden' : 'overflow-y-auto p-6 lg:p-8'"
    >
      <RouterView />
    </main>

    <AgentFormDialog
      ref="editDialog"
      mode="edit"
      :agent="agent"
    />
  </div>
</template>
