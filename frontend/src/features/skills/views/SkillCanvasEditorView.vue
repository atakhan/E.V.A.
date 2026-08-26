<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import CanvasToolbar from "@/features/skills/components/CanvasToolbar.vue";
import CanvasFloatingBar from "@/features/skills/components/CanvasFloatingBar.vue";
import FsmCanvas from "@/features/skills/components/FsmCanvas.vue";
import SkillInspector from "@/features/skills/components/SkillInspector.vue";
import { useSkills } from "@/features/skills/composables/useSkills";
import type { CanvasTool, FsmEditorState, FsmSelection } from "@/features/skills/types/fsm";
import { createEmptyFsmEditorState } from "@/features/skills/types/skill";
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

const editorState = ref<FsmEditorState>(createEmptyFsmEditorState());
const yamlOpen = ref(false);
const yamlText = ref("");
const yamlError = ref<string | null>(null);
const yamlMode = ref<"export" | "import">("export");

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

const skillTitle = computed(() => skill.value?.name ?? "Skill");

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
</script>

<template>
  <div v-if="skill" class="relative flex h-screen">
    <div class="relative min-w-0 flex-1">
      <FsmCanvas
        :key="`${agentSlug}:${skillId}`"
        v-model="editorState"
        v-model:selection="selection"
        :active-tool="activeTool"
      />
      <CanvasFloatingBar
        :title="skillTitle"
        @home="goHome"
        @export-yaml="openExport"
        @import-yaml="openImport"
      />
      <CanvasToolbar v-model:active-tool="activeTool" />
    </div>

    <SkillInspector
      v-model="editorState"
      v-model:selection="selection"
      :agent-slug="agentSlug"
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
  <div v-else class="flex h-screen items-center justify-center bg-base-200">
    <p class="text-sm text-base-content/60">Skill не найден</p>
  </div>
</template>
