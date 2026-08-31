<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import type { ActionDef, ActionRecipeStep } from "@/features/actions/types/action";
import {
  formatJsonSchema,
  isValidActionVersion,
  parseJsonSchema,
} from "@/features/actions/types/normalize";
import RecipeStepEditor from "@/features/actions/components/RecipeStepEditor.vue";
import { useActions } from "@/features/actions/composables/useActions";
import { useTools } from "@/features/tools/composables/useTools";

const props = defineProps<{
  agentSlug: string;
  action: ActionDef;
}>();

const emit = defineEmits<{
  deleted: [];
  "action-id-changed": [newId: string];
}>();

const {
  updateAction,
  deleteAction,
  addRecipeStep,
  updateRecipeStep,
  removeRecipeStep,
  moveRecipeStep,
} = useActions();

const { getEnabledInstances, getToolCommandIds } = useTools();

const menuOpen = ref(false);
const advancedOpen = ref(false);
const idModalOpen = ref(false);
const expandedStepId = ref<string | null>(null);

const formName = ref(props.action.name);
const formDescription = ref(props.action.description);
const formVersion = ref(props.action.version);
const formPolicy = ref(props.action.policy);
const formInputSchema = ref(formatJsonSchema(props.action.inputSchema));
const formOutputSchema = ref(formatJsonSchema(props.action.outputSchema));
const formNewId = ref(props.action.id);
const formError = ref<string | null>(null);
const advancedDirty = ref(false);

let autosaveTimer: ReturnType<typeof setTimeout> | null = null;

const recipe = computed(() => props.action.recipe);
const enabledInstances = computed(() => getEnabledInstances(props.agentSlug));
const recipeStepIds = computed(() => recipe.value.map((step) => step.id));

const advancedHasWarning = computed(
  () =>
    !isValidActionVersion(formVersion.value) ||
    formInputSchema.value.trim() !== "{}" ||
    formOutputSchema.value.trim() !== "{}",
);

watch(
  () => props.action,
  (action) => {
    formName.value = action.name;
    formDescription.value = action.description;
    formVersion.value = action.version;
    formPolicy.value = action.policy;
    formInputSchema.value = formatJsonSchema(action.inputSchema);
    formOutputSchema.value = formatJsonSchema(action.outputSchema);
    formNewId.value = action.id;
    formError.value = null;
    advancedDirty.value = false;
    expandedStepId.value = action.recipe[0]?.id ?? null;
  },
  { deep: true, immediate: true },
);

function scheduleAutosave() {
  if (autosaveTimer) clearTimeout(autosaveTimer);
  autosaveTimer = setTimeout(() => {
    const result = updateAction(props.agentSlug, props.action.id, {
      name: formName.value,
      description: formDescription.value,
    });
    if (!result.ok) formError.value = result.error;
  }, 500);
}

watch([formName, formDescription], () => scheduleAutosave());

onUnmounted(() => {
  if (autosaveTimer) clearTimeout(autosaveTimer);
});

function markAdvancedDirty() {
  advancedDirty.value = true;
}

function saveAdvanced() {
  formError.value = null;
  const result = updateAction(props.agentSlug, props.action.id, {
    version: formVersion.value,
    policy: formPolicy.value,
    inputSchema: parseJsonSchema(formInputSchema.value),
    outputSchema: parseJsonSchema(formOutputSchema.value),
  });
  if (!result.ok) {
    formError.value = result.error;
    return;
  }
  advancedDirty.value = false;
}

function openIdModal() {
  formNewId.value = props.action.id;
  formError.value = null;
  idModalOpen.value = true;
  menuOpen.value = false;
}

function saveNewId() {
  formError.value = null;
  const result = updateAction(props.agentSlug, props.action.id, { id: formNewId.value });
  if (!result.ok) {
    formError.value = result.error;
    return;
  }
  idModalOpen.value = false;
  emit("action-id-changed", formNewId.value);
}

function patchStep(step: ActionRecipeStep, patch: Partial<ActionRecipeStep>) {
  const next = { ...patch };
  if (patch.tool !== undefined && patch.tool !== step.tool) {
    const commands = getToolCommandIds(patch.tool);
    if (!commands.includes(step.command)) {
      next.command = commands[0] ?? "";
    }
  }
  updateRecipeStep(props.agentSlug, props.action.id, step.id, next);
}

watch(
  () => props.action.recipe.length,
  (len, prevLen) => {
    if (len > (prevLen ?? 0)) {
      expandedStepId.value = props.action.recipe[len - 1]?.id ?? null;
    }
  },
);

function addStep() {
  const instance = enabledInstances.value[0];
  const typeId = instance?.toolId ?? "";
  const command = typeId ? getToolCommandIds(typeId)[0] ?? "" : "";
  addRecipeStep(props.agentSlug, props.action.id, { tool: instance?.id ?? typeId, command });
}

function toggleStep(stepId: string) {
  expandedStepId.value = expandedStepId.value === stepId ? null : stepId;
}

function remove() {
  if (!confirm(`Удалить Action «${props.action.name}»?`)) return;
  deleteAction(props.agentSlug, props.action.id);
  menuOpen.value = false;
  emit("deleted");
}

function onStepRemoved(stepId: string) {
  if (expandedStepId.value === stepId) {
    expandedStepId.value = props.action.recipe.find((s) => s.id !== stepId)?.id ?? null;
  }
  removeRecipeStep(props.agentSlug, props.action.id, stepId);
}
</script>

<template>
  <section class="space-y-4">
    <div class="rounded-2xl border border-base-300 bg-base-100 p-4 shadow-sm">
      <div class="flex items-start gap-2">
        <div class="min-w-0 flex-1 space-y-2">
          <input
            v-model="formName"
            class="input input-ghost w-full px-0 text-lg font-semibold focus:outline-none"
            placeholder="Название Action"
          />
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-mono text-xs text-base-content/50">{{ action.id }}</span>
            <input
              v-model="formDescription"
              class="input input-ghost input-xs min-w-0 flex-1 font-normal text-base-content/70 focus:outline-none"
              placeholder="Описание…"
            />
          </div>
        </div>
        <div class="relative shrink-0">
          <button
            type="button"
            class="btn btn-sm btn-square btn-ghost"
            aria-label="Меню"
            @click="menuOpen = !menuOpen"
          >
            ⋯
          </button>
          <div
            v-if="menuOpen"
            class="absolute right-0 top-full z-10 mt-1 w-44 rounded-box border border-base-300 bg-base-100 py-1 shadow-lg"
          >
            <button type="button" class="btn btn-ghost btn-sm w-full justify-start" @click="openIdModal">
              Редактировать id
            </button>
            <button
              type="button"
              class="btn btn-ghost btn-sm w-full justify-start text-error"
              @click="remove"
            >
              Удалить
            </button>
          </div>
        </div>
      </div>
      <p v-if="formError && !idModalOpen && !advancedOpen" class="mt-2 text-xs text-error">{{ formError }}</p>
    </div>

    <div class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h4 class="font-semibold">Recipe · {{ recipe.length }} steps</h4>
          <p class="mt-1 text-sm text-base-content/60">
            Шаги из подключённых Tools — FSM вызывает Action целиком
          </p>
        </div>
        <button
          type="button"
          class="btn btn-sm"
          :disabled="enabledInstances.length === 0"
          @click="addStep"
        >
          Добавить шаг
        </button>
      </div>

      <p v-if="enabledInstances.length === 0" class="mt-3 text-sm text-warning">
        Нет подключённых Tools. Включите хотя бы один в разделе Tools.
      </p>

      <div
        v-if="recipe.length === 0"
        class="mt-4 rounded-xl border border-dashed border-base-300 bg-base-200/40 px-4 py-8 text-center text-sm text-base-content/60"
      >
        Пока нет шагов. Добавьте шаг recipe из подключённого Tool.
      </div>

      <ol v-else class="mt-4 space-y-2">
        <RecipeStepEditor
          v-for="(step, index) in recipe"
          :key="step.id"
          :agent-slug="agentSlug"
          :step="step"
          :index="index"
          :total="recipe.length"
          :step-ids="recipeStepIds"
          :expanded="expandedStepId === step.id"
          @toggle="toggleStep(step.id)"
          @patch="patchStep(step, $event)"
          @move="moveRecipeStep(agentSlug, action.id, step.id, $event)"
          @remove="onStepRemoved(step.id)"
        />
      </ol>
    </div>

    <div class="rounded-2xl border border-base-300 bg-base-100 shadow-sm">
      <button
        type="button"
        class="flex w-full items-center justify-between px-5 py-3 text-left"
        @click="advancedOpen = !advancedOpen"
      >
        <span class="text-sm font-semibold">Advanced</span>
        <span class="flex items-center gap-2 text-xs text-base-content/50">
          <span v-if="advancedHasWarning" class="badge badge-xs badge-warning">!</span>
          <span v-if="advancedDirty" class="badge badge-xs badge-ghost">unsaved</span>
          {{ advancedOpen ? "▾" : "▸" }}
        </span>
      </button>

      <div v-if="advancedOpen" class="space-y-3 border-t border-base-300 px-5 py-4">
        <div class="grid gap-3 sm:grid-cols-2">
          <label class="form-control w-full">
            <span class="label-text">Version (SemVer)</span>
            <input
              v-model="formVersion"
              class="input input-bordered input-sm w-full font-mono"
              placeholder="0.1.0"
              @input="markAdvancedDirty"
            />
          </label>
          <label class="form-control w-full">
            <span class="label-text">Policy</span>
            <select
              v-model="formPolicy"
              class="select select-bordered select-sm w-full"
              @change="markAdvancedDirty"
            >
              <option value="auto">auto</option>
              <option value="needs_human">needs_human</option>
            </select>
          </label>
        </div>

        <div class="grid gap-3 sm:grid-cols-2">
          <label class="form-control w-full">
            <span class="label-text">Input schema (JSON)</span>
            <textarea
              v-model="formInputSchema"
              class="textarea textarea-bordered textarea-sm w-full font-mono text-xs"
              rows="3"
              placeholder='{"type":"object"}'
              @input="markAdvancedDirty"
            />
          </label>
          <label class="form-control w-full">
            <span class="label-text">Output schema (JSON)</span>
            <textarea
              v-model="formOutputSchema"
              class="textarea textarea-bordered textarea-sm w-full font-mono text-xs"
              rows="3"
              placeholder='{"type":"object"}'
              @input="markAdvancedDirty"
            />
          </label>
        </div>

        <div class="flex items-center justify-between gap-2 rounded-lg border border-base-300 bg-base-200/30 px-3 py-2">
          <div>
            <p class="text-xs text-base-content/50">Action id (для FSM)</p>
            <p class="font-mono text-sm">{{ action.id }}</p>
          </div>
          <button type="button" class="btn btn-xs" @click="openIdModal">Изменить</button>
        </div>

        <p v-if="formError" class="text-sm text-error">{{ formError }}</p>

        <div class="flex justify-end">
          <button
            type="button"
            class="btn btn-sm"
            :disabled="!advancedDirty"
            @click="saveAdvanced"
          >
            Сохранить Advanced
          </button>
        </div>
      </div>
    </div>

    <dialog class="modal" :class="{ 'modal-open': idModalOpen }">
      <div class="modal-box">
        <h3 class="text-lg font-semibold">Редактировать Action id</h3>
        <p class="mt-1 text-sm text-base-content/60">
          Обновит ссылки в Skills FSM автоматически.
        </p>
        <label class="form-control mt-4 w-full">
          <span class="label-text">ID</span>
          <input v-model="formNewId" class="input input-bordered w-full font-mono" />
        </label>
        <p v-if="formError" class="mt-2 text-sm text-error">{{ formError }}</p>
        <div class="modal-action">
          <button type="button" class="btn btn-ghost" @click="idModalOpen = false">Отмена</button>
          <button type="button" class="btn" @click="saveNewId">Сохранить</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @submit.prevent="idModalOpen = false">
        <button type="submit">close</button>
      </form>
    </dialog>
  </section>
</template>
