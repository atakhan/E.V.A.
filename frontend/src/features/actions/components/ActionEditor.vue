<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { ActionDef, ActionRecipeStep } from "@/features/actions/types/action";
import { formatRecipeStepLabel } from "@/features/actions/types/normalize";
import { useActions } from "@/features/actions/composables/useActions";
import { useTools } from "@/features/tools/composables/useTools";
import { formatToolCommand } from "@/features/tools/registry/builtinTools";

const props = defineProps<{
  agentSlug: string;
  action: ActionDef;
}>();

const emit = defineEmits<{
  deleted: [];
}>();

const {
  updateAction,
  deleteAction,
  addRecipeStep,
  updateRecipeStep,
  removeRecipeStep,
  moveRecipeStep,
} = useActions();

const {
  getEnabledToolIds,
  getToolCommandIds,
  getToolDefinition,
  isToolEnabled,
} = useTools();

const formId = ref(props.action.id);
const formName = ref(props.action.name);
const formDescription = ref(props.action.description);
const formError = ref<string | null>(null);
const dirtyMeta = ref(false);

watch(
  () => props.action,
  (action) => {
    if (dirtyMeta.value) return;
    formId.value = action.id;
    formName.value = action.name;
    formDescription.value = action.description;
    formError.value = null;
  },
  { deep: true },
);

const recipe = computed(() => props.action.recipe);
const enabledToolIds = computed(() => getEnabledToolIds(props.agentSlug));

function markDirty() {
  dirtyMeta.value = true;
}

function saveMeta() {
  formError.value = null;
  const result = updateAction(props.agentSlug, props.action.id, {
    id: formId.value,
    name: formName.value,
    description: formDescription.value,
  });
  if (!result.ok) {
    formError.value = result.error;
    return;
  }
  dirtyMeta.value = false;
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

function stepStatus(step: ActionRecipeStep): "ok" | "disabled" | "unknown" {
  if (!step.tool) return "unknown";
  const def = getToolDefinition(step.tool);
  if (!def) return "unknown";
  if (!isToolEnabled(props.agentSlug, step.tool)) return "disabled";
  if (step.command && !def.commands.some((command) => command.id === step.command)) {
    return "unknown";
  }
  return "ok";
}

function commandsFor(toolId: string): string[] {
  return getToolCommandIds(toolId);
}

function addStep() {
  const toolId = enabledToolIds.value[0] ?? "";
  const command = toolId ? getToolCommandIds(toolId)[0] ?? "" : "";
  addRecipeStep(props.agentSlug, props.action.id, { tool: toolId, command });
}

function remove() {
  if (!confirm(`Удалить Action «${props.action.name}»?`)) return;
  deleteAction(props.agentSlug, props.action.id);
  emit("deleted");
}
</script>

<template>
  <section class="space-y-6">
    <div class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 class="text-lg font-semibold">{{ action.name }}</h3>
          <p class="mt-1 font-mono text-xs text-base-content/50">{{ action.id }}</p>
        </div>
        <button type="button" class="btn btn-xs btn-ghost text-error" @click="remove">
          Удалить
        </button>
      </div>

      <div class="mt-4 grid gap-3 sm:grid-cols-2">
        <label class="form-control w-full">
          <span class="label-text">Название</span>
          <input
            v-model="formName"
            class="input input-bordered input-sm w-full"
            @input="markDirty"
          />
        </label>
        <label class="form-control w-full">
          <span class="label-text">ID (для FSM)</span>
          <input
            v-model="formId"
            class="input input-bordered input-sm w-full font-mono"
            @input="markDirty"
          />
        </label>
      </div>

      <label class="form-control mt-3 w-full">
        <span class="label-text">Описание</span>
        <textarea
          v-model="formDescription"
          class="textarea textarea-bordered textarea-sm w-full"
          rows="2"
          @input="markDirty"
        />
      </label>

      <p v-if="formError" class="mt-2 text-sm text-error">{{ formError }}</p>

      <div class="mt-3 flex justify-end">
        <button
          type="button"
          class="btn btn-sm"
          :disabled="!dirtyMeta"
          @click="saveMeta"
        >
          Сохранить
        </button>
      </div>
    </div>

    <div class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h4 class="font-semibold">Recipe</h4>
          <p class="mt-1 text-sm text-base-content/60">
            Шаги из подключённых Tools — FSM вызывает Action целиком
          </p>
        </div>
        <button
          type="button"
          class="btn btn-sm"
          :disabled="enabledToolIds.length === 0"
          @click="addStep"
        >
          Добавить шаг
        </button>
      </div>

      <p
        v-if="enabledToolIds.length === 0"
        class="mt-3 text-sm text-warning"
      >
        Нет подключённых Tools. Включите хотя бы один в разделе Tools.
      </p>

      <div
        v-if="recipe.length === 0"
        class="mt-4 rounded-xl border border-dashed border-base-300 bg-base-200/40 px-4 py-8 text-center text-sm text-base-content/60"
      >
        Пока нет шагов. Добавьте, например,
        <span class="font-mono">{{ formatToolCommand("llm", "run_structured") }}</span>
      </div>

      <ol v-else class="mt-4 space-y-3">
        <li
          v-for="(step, index) in recipe"
          :key="step.id"
          class="rounded-xl border p-4"
          :class="
            stepStatus(step) === 'ok'
              ? 'border-base-300 bg-base-200/30'
              : 'border-warning/50 bg-warning/5'
          "
        >
          <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
            <p class="text-xs font-semibold uppercase tracking-wide text-base-content/50">
              Шаг {{ index + 1 }} · {{ formatRecipeStepLabel(step) }}
              <span v-if="stepStatus(step) === 'disabled'" class="text-warning"> · tool off</span>
              <span v-else-if="stepStatus(step) === 'unknown'" class="text-warning"> · unknown</span>
            </p>
            <div class="flex gap-1">
              <button
                type="button"
                class="btn btn-xs btn-ghost"
                :disabled="index === 0"
                @click="moveRecipeStep(agentSlug, action.id, step.id, -1)"
              >
                ↑
              </button>
              <button
                type="button"
                class="btn btn-xs btn-ghost"
                :disabled="index === recipe.length - 1"
                @click="moveRecipeStep(agentSlug, action.id, step.id, 1)"
              >
                ↓
              </button>
              <button
                type="button"
                class="btn btn-xs btn-ghost text-error"
                @click="removeRecipeStep(agentSlug, action.id, step.id)"
              >
                Удалить
              </button>
            </div>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <label class="form-control w-full">
              <span class="label-text">Tool</span>
              <select
                class="select select-bordered select-sm w-full font-mono"
                :value="step.tool"
                @change="patchStep(step, { tool: ($event.target as HTMLSelectElement).value })"
              >
                <option v-if="step.tool && !enabledToolIds.includes(step.tool)" :value="step.tool">
                  {{ step.tool }} (не подключён)
                </option>
                <option v-for="toolId in enabledToolIds" :key="toolId" :value="toolId">
                  {{ getToolDefinition(toolId)?.name ?? toolId }} ({{ toolId }})
                </option>
              </select>
            </label>
            <label class="form-control w-full">
              <span class="label-text">Command</span>
              <select
                class="select select-bordered select-sm w-full font-mono"
                :value="step.command"
                :disabled="!step.tool"
                @change="patchStep(step, { command: ($event.target as HTMLSelectElement).value })"
              >
                <option
                  v-if="step.command && !commandsFor(step.tool).includes(step.command)"
                  :value="step.command"
                >
                  {{ step.command }} (нет в каталоге)
                </option>
                <option
                  v-for="commandId in commandsFor(step.tool)"
                  :key="commandId"
                  :value="commandId"
                >
                  {{ commandId }}
                </option>
              </select>
            </label>
          </div>

          <label class="form-control mt-3 w-full">
            <span class="label-text">Args (свободно, JSON/заметки)</span>
            <textarea
              class="textarea textarea-bordered textarea-sm w-full font-mono text-xs"
              rows="2"
              :value="step.args"
              placeholder='{"schema":"ParsedRequestV1"}'
              @change="patchStep(step, { args: ($event.target as HTMLTextAreaElement).value })"
            />
          </label>
        </li>
      </ol>
    </div>
  </section>
</template>
