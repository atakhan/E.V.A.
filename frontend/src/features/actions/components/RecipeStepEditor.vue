<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { ActionRecipeStep } from "@/features/actions/types/action";
import { formatStepInput, parseStepInput } from "@/features/actions/types/normalize";
import TemplateChipBar from "@/features/actions/components/TemplateChipBar.vue";
import {
  genericFieldsFromInput,
  getRecipeInputFields,
  objectToPresetValues,
  presetInputToObject,
  type RecipeInputField,
} from "@/features/actions/utils/recipeInputPresets";
import {
  getRecipeStepStatus,
  recipeStepSummary,
} from "@/features/actions/utils/actionSidebarMeta";
import { getAgentBySlug } from "@/features/agents/services/agentsStorage";
import { useTools } from "@/features/tools/composables/useTools";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";
import { resolveRecipeTool, instanceLabel } from "@/features/tools/utils/resolveToolInstance";

const props = defineProps<{
  agentSlug: string;
  step: ActionRecipeStep;
  index: number;
  total: number;
  stepIds: string[];
  expanded: boolean;
}>();

const emit = defineEmits<{
  toggle: [];
  patch: [patch: Partial<ActionRecipeStep>];
  move: [delta: -1 | 1];
  remove: [];
}>();

const { getEnabledInstances, getToolCommandIds } = useTools();

const rawJsonMode = ref(false);
const fieldValues = ref<Record<string, string>>({});
const rawJson = ref(formatStepInput(props.step));
const whenOpen = ref(Boolean(props.step.when?.trim()));

const agent = computed(() => getAgentBySlug(props.agentSlug));
const enabledInstances = computed(() => getEnabledInstances(props.agentSlug));

const stepStatus = computed(() => {
  if (!agent.value) return "unknown" as const;
  return getRecipeStepStatus(agent.value, props.step);
});

const resolvedStep = computed(() =>
  agent.value && props.step.tool ? resolveRecipeTool(agent.value, props.step.tool) : null,
);

const summary = computed(() =>
  agent.value ? recipeStepSummary(agent.value, props.step) : props.step.tool,
);

const commandDescription = computed(() => {
  const typeId = resolvedStep.value?.typeId ?? props.step.tool;
  const def = typeId ? getToolDefinition(typeId) : undefined;
  return def?.commands.find((command) => command.id === props.step.command)?.description ?? "";
});

const presetFields = computed<RecipeInputField[] | null>(() => {
  const typeId = resolvedStep.value?.typeId ?? props.step.tool;
  if (!typeId || !props.step.command) return null;
  return getRecipeInputFields(typeId, props.step.command);
});

const activeFields = computed(() => {
  if (presetFields.value) return presetFields.value;
  return genericFieldsFromInput(props.step.input);
});

function statusBadgeClass(): string {
  if (stepStatus.value === "disabled") return "badge-warning";
  if (stepStatus.value === "unknown") return "badge-warning";
  return "badge-ghost";
}

function commandsFor(instanceId: string): string[] {
  const typeId = resolveRecipeTool(agent.value ?? { tools: [] }, instanceId).typeId || instanceId;
  return getToolCommandIds(typeId);
}

function patchTool(instanceId: string) {
  const typeId = resolveRecipeTool(agent.value ?? { tools: [] }, instanceId).typeId || instanceId;
  const commands = getToolCommandIds(typeId);
  emit("patch", {
    tool: instanceId,
    command: commands.includes(props.step.command) ? props.step.command : commands[0] ?? "",
  });
}

function syncFieldsFromStep() {
  if (presetFields.value) {
    fieldValues.value = objectToPresetValues(presetFields.value, props.step.input);
  } else {
    fieldValues.value = Object.fromEntries(
      Object.entries(props.step.input).map(([key, value]) => [
        key,
        typeof value === "object" ? JSON.stringify(value) : String(value ?? ""),
      ]),
    );
  }
  rawJson.value = formatStepInput(props.step);
  whenOpen.value = Boolean(props.step.when?.trim());
}

watch(
  () => props.step,
  () => syncFieldsFromStep(),
  { deep: true, immediate: true },
);

function applyPresetFields() {
  const nextInput = presetFields.value
    ? presetInputToObject(presetFields.value, fieldValues.value)
    : presetInputToObject(activeFields.value, fieldValues.value);
  emit("patch", { input: nextInput });
}

function applyRawJson() {
  emit("patch", { input: parseStepInput(rawJson.value) });
}

function setFieldValue(key: string, value: string) {
  fieldValues.value = { ...fieldValues.value, [key]: value };
  applyPresetFields();
}

function openWhen() {
  whenOpen.value = true;
}

function clearWhen() {
  whenOpen.value = false;
  emit("patch", { when: undefined });
}
</script>

<template>
  <li
    class="rounded-xl border"
    :class="
      stepStatus === 'ok'
        ? 'border-base-300 bg-base-200/30'
        : 'border-warning/50 bg-warning/5'
    "
  >
    <div class="flex items-center gap-2 px-3 py-2">
      <button
        type="button"
        class="flex min-w-0 flex-1 items-center gap-2 text-left text-xs"
        @click="emit('toggle')"
      >
        <span class="text-base-content/50">{{ index + 1 }}</span>
        <span class="truncate font-mono font-medium">{{ summary }}</span>
        <span class="badge badge-xs shrink-0" :class="statusBadgeClass()">
          {{ stepStatus === "ok" ? "ok" : stepStatus === "disabled" ? "tool off" : "?" }}
        </span>
        <span class="ml-auto text-base-content/40">{{ expanded ? "▾" : "▸" }}</span>
      </button>
      <div class="flex shrink-0 gap-0.5">
        <button
          type="button"
          class="btn btn-xs btn-ghost"
          :disabled="index === 0"
          @click.stop="emit('move', -1)"
        >
          ↑
        </button>
        <button
          type="button"
          class="btn btn-xs btn-ghost"
          :disabled="index === total - 1"
          @click.stop="emit('move', 1)"
        >
          ↓
        </button>
        <button type="button" class="btn btn-xs btn-ghost text-error" @click.stop="emit('remove')">
          ×
        </button>
      </div>
    </div>

    <div v-if="expanded" class="space-y-3 border-t border-base-300/60 px-3 py-3">
      <div class="grid gap-3 sm:grid-cols-2">
        <label class="form-control w-full">
          <span class="label-text">Tool instance</span>
          <select
            class="select select-bordered select-sm w-full font-mono"
            :value="step.tool"
            @change="patchTool(($event.target as HTMLSelectElement).value)"
          >
            <option
              v-if="step.tool && !enabledInstances.some((item) => item.id === step.tool)"
              :value="step.tool"
            >
              {{ step.tool }} (не подключён)
            </option>
            <option v-for="instance in enabledInstances" :key="instance.id" :value="instance.id">
              {{ instanceLabel(instance) }}
            </option>
          </select>
        </label>
        <label class="form-control w-full">
          <span class="label-text">Command</span>
          <select
            class="select select-bordered select-sm w-full font-mono"
            :value="step.command"
            :disabled="!step.tool"
            @change="emit('patch', { command: ($event.target as HTMLSelectElement).value })"
          >
            <option
              v-if="step.command && !commandsFor(step.tool).includes(step.command)"
              :value="step.command"
            >
              {{ step.command }} (нет в каталоге)
            </option>
            <option v-for="commandId in commandsFor(step.tool)" :key="commandId" :value="commandId">
              {{ commandId }}
            </option>
          </select>
        </label>
      </div>

      <p v-if="commandDescription" class="text-xs text-base-content/55">{{ commandDescription }}</p>

      <div class="flex items-center justify-between gap-2">
        <span class="label-text">Input</span>
        <label class="label cursor-pointer gap-2 py-0">
          <span class="label-text text-xs">Raw JSON</span>
          <input v-model="rawJsonMode" type="checkbox" class="toggle toggle-xs" />
        </label>
      </div>

      <template v-if="rawJsonMode">
        <textarea
          v-model="rawJson"
          class="textarea textarea-bordered textarea-sm w-full font-mono text-xs"
          rows="4"
          @change="applyRawJson"
        />
      </template>
      <template v-else>
        <TemplateChipBar :step-ids="stepIds" />
        <div class="mt-2 space-y-2">
          <label
            v-for="field in activeFields"
            :key="field.key"
            class="form-control w-full"
          >
            <span class="label-text text-xs">{{ field.label }}</span>
            <textarea
              v-if="field.kind === 'json'"
              class="textarea textarea-bordered textarea-sm w-full font-mono text-xs"
              rows="2"
              :value="fieldValues[field.key] ?? ''"
              :placeholder="field.placeholder"
              @input="setFieldValue(field.key, ($event.target as HTMLTextAreaElement).value)"
            />
            <input
              v-else
              class="input input-bordered input-sm w-full font-mono text-xs"
              :value="fieldValues[field.key] ?? ''"
              :placeholder="field.placeholder"
              @input="setFieldValue(field.key, ($event.target as HTMLInputElement).value)"
            />
          </label>
        </div>
      </template>

      <div v-if="whenOpen || step.when" class="space-y-1">
        <div class="flex items-center justify-between gap-2">
          <span class="label-text">When (guard)</span>
          <button type="button" class="btn btn-ghost btn-xs" @click="clearWhen">убрать</button>
        </div>
        <input
          class="input input-bordered input-sm w-full font-mono text-xs"
          :value="step.when || ''"
          placeholder="steps.crm.result.count == 0"
          @change="emit('patch', { when: ($event.target as HTMLInputElement).value })"
        />
        <span class="text-[10px] text-base-content/45">
          Guard для шага recipe: result.*, steps.*, input.*, vars.*
        </span>
      </div>
      <button v-else type="button" class="btn btn-ghost btn-xs" @click="openWhen">
        + When (guard)
      </button>
    </div>
  </li>
</template>
