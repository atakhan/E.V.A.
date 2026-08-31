<script setup lang="ts">
import { computed, ref, useTemplateRef, watch } from "vue";
import { useRouter } from "vue-router";
import type { AgentIssue } from "@/features/agents/utils/validateAgent";
import CanvasToolbar from "@/features/skills/components/CanvasToolbar.vue";
import CanvasFloatingBar from "@/features/skills/components/CanvasFloatingBar.vue";
import FsmCanvas from "@/features/skills/components/FsmCanvas.vue";
import SkillInspector from "@/features/skills/components/SkillInspector.vue";
import { useSkillValidation } from "@/features/skills/composables/useSkillValidation";
import { useSkills } from "@/features/skills/composables/useSkills";
import type { CanvasTool, FsmEditorState, FsmSelection } from "@/features/skills/types/fsm";
import { createEmptyFsmEditorState } from "@/features/skills/types/skill";
import { filterIssuesForSelection } from "@/features/skills/utils/skillIssueIndex";
import { skillFromYaml, skillToYaml } from "@/features/skills/utils/skillYaml";
import { agentSkillsPath } from "@/router/paths";

const props = defineProps<{
  agentSlug: string;
  skillId: string;
}>();

const router = useRouter();
const { getSkill, replaceSkillFsm, updateSkill } = useSkills();

const activeTool = ref<CanvasTool>("select");
const selection = ref<FsmSelection>(null);
const skill = computed(() => getSkill(props.agentSlug, props.skillId));
const canvasRef = useTemplateRef<InstanceType<typeof FsmCanvas>>("canvas");

const editorState = ref<FsmEditorState>(createEmptyFsmEditorState());
const yamlOpen = ref(false);
const yamlText = ref("");
const yamlError = ref<string | null>(null);
const yamlMode = ref<"export" | "import">("export");
const validationOpen = ref(true);

const { issues, errors, warnings, issueMaps } = useSkillValidation(
  () => props.agentSlug,
  skill,
  editorState,
);

const visibleIssues = computed(() => {
  if (!selection.value) return issues.value;
  return filterIssuesForSelection(issues.value, selection.value);
});

function loadEditorState() {
  const value = getSkill(props.agentSlug, props.skillId);
  if (!value) return;
  editorState.value = {
    initial: value.initial,
    params: value.params.map((param) => ({ ...param })),
    states: value.states.map((state) => ({
      ...state,
      onEnter: [...state.onEnter],
      transitions: state.transitions.map((transition) => ({
        ...transition,
        actions: [...transition.actions],
      })),
    })),
    viewport: { ...value.viewport },
  };
  selection.value = null;
}

watch(
  () => [props.agentSlug, props.skillId] as const,
  () => loadEditorState(),
  { immediate: true },
);

watch(
  editorState,
  (value) => {
    if (!getSkill(props.agentSlug, props.skillId)) return;
    replaceSkillFsm(props.agentSlug, props.skillId, value);
  },
  { deep: true },
);

async function goHome() {
  await router.push(agentSkillsPath(props.agentSlug));
}

function openExport() {
  const current = getSkill(props.agentSlug, props.skillId);
  if (!current) return;
  yamlMode.value = "export";
  yamlError.value = null;
  yamlText.value = skillToYaml(current);
  yamlOpen.value = true;
}

function openImport() {
  yamlMode.value = "import";
  yamlError.value = null;
  yamlText.value = "";
  yamlOpen.value = true;
}

function applyImport() {
  const current = getSkill(props.agentSlug, props.skillId);
  if (!current) return;
  const result = skillFromYaml(yamlText.value, current);
  if ("error" in result) {
    yamlError.value = result.error;
    return;
  }
  updateSkill(props.agentSlug, props.skillId, {
    description: result.description,
    version: result.version,
    initial: result.initial,
    params: result.params,
    states: result.states,
  });
  loadEditorState();
  yamlOpen.value = false;
}

async function copyYaml() {
  try {
    await navigator.clipboard.writeText(yamlText.value);
  } catch {
    // ignore
  }
}

function onSelectIssue(issue: AgentIssue) {
  validationOpen.value = true;
  const locator = issue.locator;
  if (!locator) return;
  if (locator.kind === "state") {
    canvasRef.value?.focusState(locator.stateId);
    return;
  }
  if (locator.kind === "transition") {
    canvasRef.value?.focusTransition(locator.stateId, locator.transitionId);
  }
}

function focusValidationPanel() {
  validationOpen.value = true;
}
</script>

<template>
  <div v-if="skill" class="relative flex min-h-0 flex-1">
    <div class="relative min-h-0 min-w-0 flex-1">
      <FsmCanvas
        ref="canvas"
        :key="`${agentSlug}:${skillId}`"
        v-model="editorState"
        v-model:selection="selection"
        :active-tool="activeTool"
        :issue-maps="issueMaps"
      />
      <CanvasFloatingBar
        :agent-slug="agentSlug"
        :skill-id="skillId"
        :error-count="errors"
        :warning-count="warnings"
        @home="goHome"
        @export-yaml="openExport"
        @import-yaml="openImport"
        @show-validation="focusValidationPanel"
      />
      <CanvasToolbar v-model:active-tool="activeTool" />
    </div>

    <SkillInspector
      v-model="editorState"
      v-model:selection="selection"
      :agent-slug="agentSlug"
      :skill-version="skill?.version"
      :skill-description="skill?.description"
      :validation-issues="visibleIssues"
      :validation-open="validationOpen"
      @update:skill-version="updateSkill(agentSlug, skillId, { version: $event })"
      @update:skill-description="updateSkill(agentSlug, skillId, { description: $event })"
      @update:validation-open="validationOpen = $event"
      @select-issue="onSelectIssue"
    />

    <dialog class="modal" :class="{ 'modal-open': yamlOpen }">
      <div class="modal-box max-w-3xl">
        <h3 class="text-lg font-semibold">
          {{ yamlMode === "export" ? "Export Skill YAML" : "Import Skill YAML" }}
        </h3>
        <textarea
          v-model="yamlText"
          class="textarea textarea-bordered mt-4 h-80 w-full font-mono text-xs"
          :readonly="yamlMode === 'export'"
        />
        <p v-if="yamlError" class="mt-2 text-sm text-error">{{ yamlError }}</p>
        <div class="modal-action">
          <button type="button" class="btn btn-ghost" @click="yamlOpen = false">Закрыть</button>
          <button
            v-if="yamlMode === 'export'"
            type="button"
            class="btn"
            @click="copyYaml"
          >
            Копировать
          </button>
          <button
            v-else
            type="button"
            class="btn"
            @click="applyImport"
          >
            Применить
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @submit.prevent="yamlOpen = false">
        <button type="submit">close</button>
      </form>
    </dialog>
  </div>
  <div v-else class="flex flex-1 items-center justify-center p-8">
    <p class="text-sm text-base-content/60">Skill не найден</p>
  </div>
</template>
