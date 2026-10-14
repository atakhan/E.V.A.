<script setup lang="ts">
import { computed, useTemplateRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import AgentFormDialog from "@/features/agents/components/AgentFormDialog.vue";
import { useAgents } from "@/features/agents/composables/useAgents";
import AgentFloatingMenu from "@/features/workspace/components/AgentFloatingMenu.vue";
import AppFloatingChrome from "@/shared/layout/AppFloatingChrome.vue";
import {
  defaultWorkspaceSectionId,
  findWorkspaceSection,
} from "@/features/workspace/config/nav";
import { agentSectionPath, RouteNames } from "@/router/paths";

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
  if (leaf === RouteNames.agentConstructor || leaf.includes("constructor")) return "constructor";
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

const isFullBleed = computed(
  () => route.name === RouteNames.skillCanvas || route.name === RouteNames.agentConstructor,
);

async function selectSection(id: string) {
  if (!agent.value) return;
  const section = findWorkspaceSection(id);
  if (!section) return;
  await router.push(agentSectionPath(agent.value.slug, section.slug));
}
</script>

<template>
  <div v-if="agent" class="flex h-screen min-h-0 bg-base-200">
    <AppFloatingChrome>
      <AgentFloatingMenu
        :agent-name="agent.name"
        :agent-slug="agent.slug"
        :active-section-id="activeSectionId"
        @select="selectSection"
        @edit="editDialog?.open()"
      />
    </AppFloatingChrome>

    <main
      class="flex min-h-0 min-w-0 flex-1 flex-col"
      :class="isFullBleed ? 'overflow-hidden' : 'overflow-y-auto px-6 pb-8 pt-[5.5rem] lg:px-8'"
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
