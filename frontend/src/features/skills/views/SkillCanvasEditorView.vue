<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import type { AgentIssue } from "@/features/agents/utils/validateAgent";
import { useActions } from "@/features/actions/composables/useActions";
import BehaviorCanvas from "@/features/skills/components/BehaviorCanvas.vue";
import BehaviorInspector from "@/features/skills/components/BehaviorInspector.vue";
import BehaviorToolbar from "@/features/skills/components/BehaviorToolbar.vue";
import CanvasFloatingBar from "@/features/skills/components/CanvasFloatingBar.vue";
import FsmCanvas from "@/features/skills/components/FsmCanvas.vue";
import { useSkillValidation } from "@/features/skills/composables/useSkillValidation";
import { useSkills } from "@/features/skills/composables/useSkills";
import { useSkillRunList } from "@/features/runtime/composables/useSkillRunList";
import { useSkillRunDetail } from "@/features/runtime/composables/useSkillRunDetail";
import type {
  BehaviorEditorState,
  BehaviorSelection,
  BehaviorTool,
  CanvasMode,
} from "@/features/skills/types/behavior";
import { emptyBehaviorEditorState, emptyBehaviorGraph } from "@/features/skills/types/behavior";
import { compileBehavior } from "@/features/skills/utils/behaviorCompile";
import { skillHasBehavior } from "@/features/skills/utils/behaviorGraph";
import { fillMissingLayouts, originNodeIdForRunState } from "@/features/skills/utils/behaviorLayout";
import { liftFsmToBehavior } from "@/features/skills/utils/behaviorLift";
import { behaviorNarrative } from "@/features/skills/utils/behaviorNarrative";
import { filterIssuesForSelection } from "@/features/skills/utils/skillIssueIndex";
import { skillFromYaml, skillToYaml } from "@/features/skills/utils/skillYaml";
import type { FsmEditorState } from "@/features/skills/types/fsm";
import { agentSkillsPath } from "@/router/paths";
import { isActiveRunStatus } from "@/features/runtime/composables/useRuntimeSummary";

const props = defineProps<{
  agentSlug: string;
  skillId: string;
}>();

const router = useRouter();
const { getSkill, replaceSkillBehavior, updateSkill } = useSkills();
const { getActions } = useActions();

const mode = ref<CanvasMode>("story");
const activeTool = ref<BehaviorTool>("select");
const selection = ref<BehaviorSelection>(null);
const skill = computed(() => getSkill(props.agentSlug, props.skillId));
const actions = computed(() => getActions(props.agentSlug));

const editor = ref<BehaviorEditorState>(emptyBehaviorEditorState());
const yamlOpen = ref(false);
const yamlText = ref("");
const yamlError = ref<string | null>(null);
const yamlMode = ref<"export" | "import">("export");
const validationOpen = ref(true);
const narrativeOpen = ref(false);
const machineOpen = ref(false);
const machineEditor = ref<FsmEditorState>({
  initial: null,
  params: [],
  states: [],
  viewport: { panX: 24, panY: 24, zoom: 0.85 },
});
const skipWatch = ref(false);

const { issues, errors, warnings, issueMaps } = useSkillValidation(
  () => props.agentSlug,
  skill,
  undefined,
  editor,
);

const visibleIssues = computed(() => filterIssuesForSelection(issues.value, selection.value));

const compilePreview = computed(() =>
  compileBehavior(editor.value.behavior, {
    actionIds: new Set(actions.value.map((item) => item.id)),
  }),
);

const compileError = computed(() => {
  const failed = compilePreview.value;
  if (failed.ok) return null;
  return failed.errors.find((item) => item.severity === "error")?.message ?? "Compile failed";
});

const execution = computed(() =>
  compilePreview.value.ok ? compilePreview.value.artifact : null,
);

const statusFilter = ref<"all">("all");
const skillIdRef = computed(() => props.skillId);
const agentSlugRef = computed(() => props.agentSlug);
const { items: runItems } = useSkillRunList({
  agentSlug: agentSlugRef,
  skillId: skillIdRef,
  statusFilter,
});
const selectedRunId = ref<string | undefined>(undefined);
const { run: liveRun } = useSkillRunDetail(selectedRunId);

watch(
  runItems,
  (items) => {
    const active = items.find((item) => isActiveRunStatus(item.status));
    if (active && !selectedRunId.value) selectedRunId.value = active.skillRunId;
  },
  { immediate: true },
);

const overlayByNode = computed(() => {
  const map: Record<string, "done" | "active" | "todo"> = {};
  if (mode.value !== "runtime") return map;
  const graph = editor.value.behavior;
  const compiled = execution.value?.states;
  const current = liveRun.value?.currentState;
  const history = liveRun.value?.history ?? [];
  for (const node of graph.nodes) map[node.id] = "todo";
  for (const stateId of history) {
    const origin = originNodeIdForRunState(stateId, graph, compiled);
    if (origin) map[origin] = "done";
  }
  if (current) {
    const origin = originNodeIdForRunState(current, graph, compiled);
    if (origin) map[origin] = "active";
  }
  return map;
});

const narrativeText = computed(() => behaviorNarrative(editor.value.behavior));

function loadEditor() {
  const value = getSkill(props.agentSlug, props.skillId);
  if (!value) return;
  skipWatch.value = true;
  let behavior = value.behavior ?? emptyBehaviorGraph();
  if (!skillHasBehavior(behavior) && value.states.length > 0) {
    behavior = fillMissingLayouts(liftFsmToBehavior(value.states, value.initial));
  } else if (skillHasBehavior(behavior)) {
    behavior = fillMissingLayouts(behavior);
  }
  editor.value = {
    behavior,
    params: value.params.map((param) => ({ ...param })),
    storyViewport: value.storyViewport ?? { panX: 40, panY: 40, zoom: 1 },
    logicViewport: value.logicViewport ?? { panX: 40, panY: 40, zoom: 1 },
  };
  selection.value = null;
  queueMicrotask(() => {
    skipWatch.value = false;
  });
}

watch(
  () => [props.agentSlug, props.skillId] as const,
  () => loadEditor(),
  { immediate: true },
);

watch(
  editor,
  (value) => {
    if (skipWatch.value) return;
    if (!getSkill(props.agentSlug, props.skillId)) return;
    replaceSkillBehavior(props.agentSlug, props.skillId, {
      behavior: value.behavior,
      params: value.params,
      storyViewport: value.storyViewport,
      logicViewport: value.logicViewport,
    });
  },
  { deep: true },
);

const currentViewport = computed({
  get: () => (mode.value === "logic" ? editor.value.logicViewport : editor.value.storyViewport),
  set: (value) => {
    if (mode.value === "logic") editor.value.logicViewport = value;
    else editor.value.storyViewport = value;
  },
});

async function goHome() {
  await router.push(agentSkillsPath(props.agentSlug));
}

function openExport() {
  const current = getSkill(props.agentSlug, props.skillId);
  if (!current) return;
  yamlMode.value = "export";
  yamlError.value = null;
  yamlText.value = skillToYaml({ ...current, behavior: editor.value.behavior });
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
    behavior: result.behavior,
  });
  loadEditor();
  yamlOpen.value = false;
}

async function copyYaml() {
  try {
    await navigator.clipboard.writeText(yamlText.value);
  } catch {
    // ignore
  }
}

function openMachine() {
  const artifact = execution.value;
  if (!artifact) return;
  machineEditor.value = {
    initial: artifact.initial,
    params: [],
    states: artifact.states.map((state) => ({
      id: state.id,
      name: state.name,
      onEnter: [...state.onEnter],
      final: state.final,
      transitions: state.transitions.map((transition) => ({ ...transition })),
      x: state.x,
      y: state.y,
      width: state.width,
      height: state.height,
      originNodeId: state.originNodeId,
    })),
    viewport: { panX: 24, panY: 24, zoom: 0.85 },
  };
  machineOpen.value = true;
}

watch(mode, () => {
  if (skipWatch.value) return;
  editor.value.behavior = fillMissingLayouts(editor.value.behavior);
});

function onSelectIssue(issue: AgentIssue) {
  validationOpen.value = true;
  const locator = issue.locator;
  if (locator?.kind === "node") {
    selection.value = { kind: "node", nodeId: locator.nodeId };
  }
}

function focusValidationPanel() {
  validationOpen.value = true;
}
</script>

<template>
  <div v-if="skill" class="relative flex min-h-0 flex-1">
    <div class="relative min-h-0 min-w-0 flex-1">
      <BehaviorCanvas
        :key="`${agentSlug}:${skillId}:${mode}`"
        v-model="editor.behavior"
        v-model:viewport="currentViewport"
        v-model:selection="selection"
        :mode="mode"
        :active-tool="activeTool"
        :actions="actions"
        :issue-maps="issueMaps"
        :read-only="mode === 'runtime'"
        :overlay-by-node="overlayByNode"
      />
      <CanvasFloatingBar
        :agent-slug="agentSlug"
        :skill-id="skillId"
        :error-count="errors"
        :warning-count="warnings"
        :mode="mode"
        @home="goHome"
        @export-yaml="openExport"
        @import-yaml="openImport"
        @show-validation="focusValidationPanel"
        @update:mode="mode = $event"
        @show-narrative="narrativeOpen = true"
      />
      <BehaviorToolbar
        v-if="mode !== 'runtime'"
        v-model:active-tool="activeTool"
      />
      <div
        v-if="mode === 'runtime'"
        class="absolute bottom-5 left-1/2 z-20 flex -translate-x-1/2 items-center gap-2 rounded-2xl border border-base-300/60 bg-base-100/90 px-3 py-2 shadow-lg"
      >
        <span class="text-xs text-base-content/60">Run</span>
        <select
          class="select select-xs"
          :value="selectedRunId"
          @change="selectedRunId = ($event.target as HTMLSelectElement).value || undefined"
        >
          <option value="">нет</option>
          <option v-for="item in runItems" :key="item.skillRunId" :value="item.skillRunId">
            {{ item.status }} · {{ item.currentState }}
          </option>
        </select>
      </div>
    </div>

    <BehaviorInspector
      v-model="editor.behavior"
      v-model:params="editor.params"
      v-model:selection="selection"
      :agent-slug="agentSlug"
      :skill-version="skill?.version"
      :skill-description="skill?.description"
      :validation-issues="visibleIssues"
      :validation-open="validationOpen"
      :execution="execution"
      :compile-error="compileError"
      @update:skill-version="updateSkill(agentSlug, skillId, { version: $event })"
      @update:skill-description="updateSkill(agentSlug, skillId, { description: $event })"
      @update:validation-open="validationOpen = $event"
      @select-issue="onSelectIssue"
      @show-machine="openMachine"
    />

    <dialog class="modal" :class="{ 'modal-open': yamlOpen }">
      <div class="modal-box max-w-3xl">
        <h3 class="text-lg font-semibold">
          {{ yamlMode === "export" ? "Канон behavior (FSM generated on publish)" : "Import Skill YAML" }}
        </h3>
        <textarea
          v-model="yamlText"
          class="textarea textarea-bordered mt-4 h-80 w-full font-mono text-xs"
          :readonly="yamlMode === 'export'"
        />
        <p v-if="yamlError" class="mt-2 text-sm text-error">{{ yamlError }}</p>
        <div class="modal-action">
          <button type="button" class="btn btn-ghost" @click="yamlOpen = false">Закрыть</button>
          <button v-if="yamlMode === 'export'" type="button" class="btn" @click="copyYaml">
            Копировать
          </button>
          <button v-else type="button" class="btn" @click="applyImport">Применить</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @submit.prevent="yamlOpen = false">
        <button type="submit">close</button>
      </form>
    </dialog>

    <dialog class="modal" :class="{ 'modal-open': narrativeOpen }">
      <div class="modal-box">
        <h3 class="text-lg font-semibold">Как историю</h3>
        <p class="mt-4 text-sm leading-relaxed">{{ narrativeText || "Пока нечего рассказать." }}</p>
        <div class="modal-action">
          <button type="button" class="btn" @click="narrativeOpen = false">Закрыть</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @submit.prevent="narrativeOpen = false">
        <button type="submit">close</button>
      </form>
    </dialog>

    <dialog class="modal" :class="{ 'modal-open': machineOpen }">
      <div class="modal-box max-w-5xl">
        <h3 class="text-lg font-semibold">Машина (read-only)</h3>
        <p class="mt-1 text-xs text-base-content/60">
          Скомпилированная FSM. Редактирование запрещено — source of truth это Behavior Graph.
        </p>
        <div class="relative mt-4 h-[420px] overflow-hidden rounded-box border border-base-300">
          <FsmCanvas v-model="machineEditor" active-tool="select" read-only />
        </div>
        <div class="modal-action">
          <button type="button" class="btn" @click="machineOpen = false">Закрыть</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @submit.prevent="machineOpen = false">
        <button type="submit">close</button>
      </form>
    </dialog>
  </div>
  <div v-else class="flex flex-1 items-center justify-center p-8">
    <p class="text-sm text-base-content/60">Skill не найден</p>
  </div>
</template>
